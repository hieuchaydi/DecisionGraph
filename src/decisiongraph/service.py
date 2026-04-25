from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date
from pathlib import Path

from decisiongraph.extractor import HeuristicExtractor
from decisiongraph.models import (
    Contradiction,
    Decision,
    Evidence,
    GuardrailResult,
    MetricSnapshot,
    QueryAnswer,
    StaleAssumption,
    utc_now_iso,
)
from decisiongraph.integrations import ingest_docs_from_git_history, ingest_docs_from_jsonl
from decisiongraph.integrations import ingest_docs_from_github_repo
from decisiongraph.integrations import ingest_docs_from_jira_json, ingest_docs_from_slack_export
from decisiongraph.reporting import build_summary_report
from decisiongraph.store import DecisionStore

ASSUMPTION_PATTERN = re.compile(
    r"(?P<metric>[a-zA-Z_][a-zA-Z0-9_\.]*)\s*(?P<op><=|>=|<|>|==)\s*(?P<threshold>[-+]?\d+(?:\.\d+)?)"
)
POSITIVE_TERMS = {"choose", "adopt", "use", "keep", "migrate", "selected", "cap"}
NEGATIVE_TERMS = {"reject", "revert", "rollback", "drop", "avoid", "remove", "deprecated"}
SENSITIVE_TAGS = {"auth", "security", "payments", "billing", "compliance", "incident-response"}
STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "from",
    "this",
    "was",
    "are",
    "why",
    "did",
    "choose",
    "decision",
    "over",
    "into",
    "when",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def _hash_text(text: str) -> str:
    normalized = "\n".join(line.strip() for line in text.splitlines()).strip().lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _contains_any(text: str, terms: set[str]) -> bool:
    tokens = _tokenize(text)
    return any(term in tokens for term in terms)


def _topic_tokens(decision: Decision) -> set[str]:
    tags = {tag.strip().lower() for tag in decision.tags if tag.strip()}
    component_tokens = _tokenize(decision.component or "")
    content_tokens = {
        tok
        for tok in _tokenize(f"{decision.title} {decision.summary}")
        if len(tok) > 3 and tok not in STOPWORDS
    }
    return tags.union(component_tokens).union(content_tokens)


def _score_decision(decision: Decision, q_tokens: set[str], question: str) -> float:
    searchable = decision.searchable_text()
    base_tokens = _tokenize(searchable)
    overlap = q_tokens.intersection(base_tokens)
    score = float(len(overlap))
    if question.lower() in searchable:
        score += 3.0
    title_tokens = _tokenize(decision.title)
    score += 0.4 * len(q_tokens.intersection(title_tokens))
    score += min(1.0, len(decision.evidence_ids) * 0.2)
    score += max(0.0, min(1.0, decision.confidence))
    return score


def _is_violation(actual: float, operator: str, threshold: float) -> bool:
    if operator == "<":
        return not actual < threshold
    if operator == "<=":
        return not actual <= threshold
    if operator == ">":
        return not actual > threshold
    if operator == ">=":
        return not actual >= threshold
    if operator == "==":
        return actual != threshold
    return False


def _stale_severity(actual: float, threshold: float) -> str:
    if threshold == 0:
        return "high"
    ratio = abs(actual - threshold) / abs(threshold)
    if ratio > 0.5:
        return "high"
    if ratio > 0.2:
        return "medium"
    return "low"


class DecisionGraphService:
    def __init__(self, store: DecisionStore, extractor: HeuristicExtractor | None = None):
        self.store = store
        self.extractor = extractor or HeuristicExtractor()

    def ingest_text(self, source_id: str, text: str, source_type: str = "note", url: str | None = None) -> Decision:
        content_hash = _hash_text(text)
        existing_evidence = self.store.find_evidence(source_type=source_type, source_id=source_id, content_hash=content_hash)
        if existing_evidence:
            linked = self.store.find_decision_by_evidence(existing_evidence.id)
            if linked:
                return linked

        decision, evidence = self.extractor.extract(text=text, source_type=source_type, source_id=source_id, url=url)
        evidence.content_hash = content_hash
        self.store.upsert(decision, [evidence])
        return decision

    def ingest_directory(self, directory: Path, pattern: str = "*.md", source_type: str = "doc") -> list[Decision]:
        inserted: list[Decision] = []
        for path in sorted(directory.rglob(pattern)):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            source_id = str(path.relative_to(directory)).replace("\\", "/")
            decision = self.ingest_text(source_id=source_id, text=text, source_type=source_type)
            inserted.append(decision)
        return inserted

    def ingest_git_history(self, repo_path: Path, max_commits: int = 200, ref: str = "HEAD") -> list[Decision]:
        docs = ingest_docs_from_git_history(repo_path=repo_path, max_commits=max_commits, ref=ref)
        inserted: list[Decision] = []
        for doc in docs:
            row = self.ingest_text(source_id=doc.source_id, text=doc.text, source_type=doc.source_type, url=doc.url)
            inserted.append(row)
        return inserted

    def ingest_jsonl(self, path: Path, default_source_type: str = "external") -> list[Decision]:
        docs = ingest_docs_from_jsonl(path=path, default_source_type=default_source_type)
        inserted: list[Decision] = []
        for doc in docs:
            row = self.ingest_text(source_id=doc.source_id, text=doc.text, source_type=doc.source_type, url=doc.url)
            inserted.append(row)
        return inserted

    def ingest_github(
        self,
        owner: str,
        repo: str,
        *,
        max_prs: int = 100,
        max_issues: int = 100,
        state: str = "all",
        token: str | None = None,
        base_url: str = "https://api.github.com",
    ) -> list[Decision]:
        docs = ingest_docs_from_github_repo(
            owner=owner,
            repo=repo,
            max_prs=max_prs,
            max_issues=max_issues,
            state=state,
            token=token,
            base_url=base_url,
        )
        inserted: list[Decision] = []
        for doc in docs:
            row = self.ingest_text(source_id=doc.source_id, text=doc.text, source_type=doc.source_type, url=doc.url)
            inserted.append(row)
        return inserted

    def ingest_slack_export(self, export_dir: Path, max_messages: int = 1000) -> list[Decision]:
        docs = ingest_docs_from_slack_export(export_dir=export_dir, max_messages=max_messages)
        inserted: list[Decision] = []
        for doc in docs:
            row = self.ingest_text(source_id=doc.source_id, text=doc.text, source_type=doc.source_type, url=doc.url)
            inserted.append(row)
        return inserted

    def ingest_jira_json(self, path: Path) -> list[Decision]:
        docs = ingest_docs_from_jira_json(path=path)
        inserted: list[Decision] = []
        for doc in docs:
            row = self.ingest_text(source_id=doc.source_id, text=doc.text, source_type=doc.source_type, url=doc.url)
            inserted.append(row)
        return inserted

    def list_decisions(
        self,
        limit: int = 50,
        *,
        query: str | None = None,
        tag: str | None = None,
        component: str | None = None,
        owner: str | None = None,
        decision_type: str | None = None,
    ) -> list[Decision]:
        rows = self.store.list_decisions(limit=10000)

        tag_filters = {part.strip().lower() for part in (tag or "").split(",") if part.strip()}
        component_filter = (component or "").strip().lower()
        owner_filter = (owner or "").strip().lower()
        decision_type_filter = (decision_type or "").strip().lower()

        filtered: list[Decision] = []
        for item in rows:
            item_tags = {entry.strip().lower() for entry in item.tags if entry.strip()}
            item_component = (item.component or "").lower()
            item_decision_type = (item.decision_type or "").lower()
            item_owners = [entry.lower() for entry in item.owners]

            if tag_filters and not tag_filters.intersection(item_tags):
                continue
            if component_filter and component_filter not in item_component:
                continue
            if owner_filter and not any(owner_filter in entry for entry in item_owners):
                continue
            if decision_type_filter and decision_type_filter != item_decision_type:
                continue
            filtered.append(item)

        query_text = (query or "").strip()
        if not query_text:
            return filtered[:limit]

        q_tokens = _tokenize(query_text)
        scored = [(item, _score_decision(item, q_tokens, query_text)) for item in filtered]
        scored.sort(key=lambda row: row[1], reverse=True)
        ranked = [item for item, score in scored if score > 0]
        return ranked[:limit]

    def get_decision(self, decision_id: str) -> Decision | None:
        return self.store.get_decision(decision_id)

    def list_metrics(self) -> list[MetricSnapshot]:
        return self.store.list_metrics()

    def set_metric(self, key: str, value: float, unit: str | None = None) -> MetricSnapshot:
        return self.store.set_metric(key=key, value=value, unit=unit)

    def _rank(self, question: str, limit: int = 3) -> list[Decision]:
        q_tokens = _tokenize(question)
        decisions = self.store.list_decisions(limit=10000)
        scored = [(item, _score_decision(item, q_tokens, question)) for item in decisions]
        scored.sort(key=lambda row: row[1], reverse=True)
        return [item for item, score in scored if score > 0][:limit]

    def query(self, question: str) -> QueryAnswer:
        ranked = self._rank(question=question, limit=5)
        if not ranked:
            return QueryAnswer(
                question=question,
                answer="No decision history found yet. Ingest PR notes or seed demo decisions first.",
                confidence=0.0,
                warnings=["decision_memory_empty"],
                decision=None,
                evidence=[],
                related=[],
            )

        best = ranked[0]
        best_score = _score_decision(best, _tokenize(question), question)

        evidence_map = self.store.get_evidence_map()
        linked_evidence = [evidence_map[eid] for eid in best.evidence_ids if eid in evidence_map]

        answer_lines = [
            f"Decision: {best.title}",
            f"Summary: {best.summary}",
            f"Date: {best.date or 'unknown'}",
        ]
        if best.owners:
            answer_lines.append(f"Owners: {', '.join(best.owners)}")
        if best.alternatives:
            answer_lines.append(f"Alternatives: {', '.join(best.alternatives)}")
        if best.tradeoffs:
            answer_lines.append(f"Trade-offs: {', '.join(best.tradeoffs)}")
        if best.assumptions:
            answer_lines.append(f"Assumptions: {', '.join(best.assumptions)}")
        if best.risks:
            answer_lines.append(f"Risks: {', '.join(best.risks)}")
        if best.component:
            answer_lines.append(f"Component: {best.component}")
        if linked_evidence:
            answer_lines.append("Evidence:")
            for item in linked_evidence[:3]:
                source = f"{item.source_type}:{item.source_id}"
                answer_lines.append(f"- {source}")

        confidence = min(0.95, max(0.35, best.confidence + (0.03 * min(3, best_score))))
        warnings: list[str] = []
        if confidence < 0.6:
            warnings.append("low_confidence")
        if not linked_evidence:
            warnings.append("no_evidence_linked")

        return QueryAnswer(
            question=question,
            answer="\n".join(answer_lines),
            confidence=round(confidence, 2),
            warnings=warnings,
            decision=best,
            evidence=linked_evidence,
            related=ranked[1:4],
        )

    def detect_contradictions(self) -> list[Contradiction]:
        decisions = self.store.list_decisions(limit=10000)
        out: list[Contradiction] = []
        for i in range(len(decisions)):
            for j in range(i + 1, len(decisions)):
                left = decisions[i]
                right = decisions[j]
                left_text = f"{left.title} {left.summary}".lower()
                right_text = f"{right.title} {right.summary}".lower()

                left_pol = 1 if _contains_any(left_text, POSITIVE_TERMS) else (-1 if _contains_any(left_text, NEGATIVE_TERMS) else 0)
                right_pol = 1 if _contains_any(right_text, POSITIVE_TERMS) else (-1 if _contains_any(right_text, NEGATIVE_TERMS) else 0)
                if left_pol == 0 or right_pol == 0 or left_pol == right_pol:
                    continue

                common_topics = _topic_tokens(left).intersection(_topic_tokens(right))
                if not common_topics:
                    continue

                topic = sorted(common_topics)[0]
                reason = f"Opposite decision polarity on shared topic '{topic}'."
                confidence = min(0.9, 0.65 + (0.05 * min(4, len(common_topics))))
                out.append(
                    Contradiction(
                        decision_a_id=left.id,
                        decision_b_id=right.id,
                        reason=reason,
                        topic=topic,
                        confidence=round(confidence, 2),
                    )
                )
        out.sort(key=lambda row: row.confidence, reverse=True)
        return out

    def detect_stale_assumptions(self, decisions: list[Decision] | None = None) -> list[StaleAssumption]:
        metrics = {row.key: row for row in self.store.list_metrics()}
        candidates = decisions or self.store.list_decisions(limit=10000)
        out: list[StaleAssumption] = []
        for item in candidates:
            for assumption in item.assumptions:
                match = ASSUMPTION_PATTERN.search(assumption)
                if not match:
                    continue
                metric_key = match.group("metric")
                operator = match.group("op")
                threshold = float(match.group("threshold"))
                snapshot = metrics.get(metric_key)
                if not snapshot:
                    continue
                if _is_violation(snapshot.value, operator, threshold):
                    out.append(
                        StaleAssumption(
                            decision_id=item.id,
                            assumption=assumption,
                            metric_key=metric_key,
                            operator=operator,
                            threshold=threshold,
                            actual=snapshot.value,
                            severity=_stale_severity(snapshot.value, threshold),
                        )
                    )
        severity_order = {"high": 0, "medium": 1, "low": 2}
        out.sort(key=lambda row: severity_order.get(row.severity, 9))
        return out

    def guardrail(self, change_request: str, limit: int = 3) -> GuardrailResult:
        related = self._rank(question=change_request, limit=max(1, limit))
        stale_related = self.detect_stale_assumptions(decisions=related)
        warnings: list[str] = []
        blocked = False

        for item in related:
            tags = {tag.lower() for tag in item.tags}
            if tags.intersection(SENSITIVE_TAGS):
                warnings.append(f"sensitive_area:{item.id}")
            if item.risks:
                warnings.append(f"known_risk:{item.id}")
            if item.confidence >= 0.8 and tags.intersection(SENSITIVE_TAGS):
                blocked = True
        for stale in stale_related:
            warnings.append(f"stale_assumption:{stale.decision_id}:{stale.metric_key}")
            if stale.severity == "high":
                blocked = True

        warnings = list(dict.fromkeys(warnings))
        return GuardrailResult(
            change_request=change_request,
            blocked=blocked,
            warnings=warnings,
            related_decisions=related,
            stale_assumptions=stale_related,
        )

    def graph_snapshot(self) -> dict[str, object]:
        decisions = self.store.list_decisions(limit=10000)
        evidence_map = self.store.get_evidence_map()
        nodes = [{"id": row.id, "type": "decision", "title": row.title} for row in decisions]
        nodes.extend({"id": ev.id, "type": "evidence", "title": f"{ev.source_type}:{ev.source_id}"} for ev in evidence_map.values())

        edges: list[dict[str, str]] = []
        for row in decisions:
            for ev_id in row.evidence_ids:
                if ev_id in evidence_map:
                    edges.append({"from": row.id, "to": ev_id, "type": "supported_by"})
            for sup in row.supersedes:
                edges.append({"from": row.id, "to": sup, "type": "supersedes"})
        return {"nodes": nodes, "edges": edges}

    def summary_report(self) -> dict[str, object]:
        decisions = self.store.list_decisions(limit=10000)
        stale = self.detect_stale_assumptions(decisions=decisions)
        contradictions = self.detect_contradictions()
        report = build_summary_report(
            generated_at=utc_now_iso(),
            decisions=decisions,
            stale_assumptions=stale,
            contradictions=contradictions,
        )
        return {"json": report.to_dict(), "markdown": report.to_markdown()}

    def seed_demo(self) -> list[Decision]:
        samples = [
            {
                "title": "Choose Redis over RabbitMQ for async workflows",
                "summary": "Operational overhead of RabbitMQ was too high for current team size.",
                "owners": ["Platform Lead"],
                "alternatives": ["RabbitMQ", "SQS"],
                "tradeoffs": ["Lower delivery guarantees for simpler operations"],
                "assumptions": ["queue_volume < 100000", "delivery_fail_rate < 0.02"],
                "risks": ["May need stronger delivery semantics later"],
                "tags": ["queues", "platform"],
                "component": "async-workflows",
                "decision_type": "architecture",
            },
            {
                "title": "Cap payment retries at 2 attempts",
                "summary": "Duplicate billing incident in 2024 shifted priority to customer trust.",
                "owners": ["Payments Team", "Finance"],
                "alternatives": ["Exponential retry up to 5 attempts"],
                "tradeoffs": ["Lower recovery rate for lower duplicate-charge risk"],
                "assumptions": ["payment_retry_error_rate < 0.03"],
                "risks": ["Revenue loss during gateway outages"],
                "tags": ["payments", "risk"],
                "component": "payment-retry",
                "decision_type": "risk-policy",
            },
            {
                "title": "Revert microservices to modular monolith",
                "summary": "Cross-service debugging and deployment complexity slowed incident response.",
                "owners": ["Architecture Group"],
                "alternatives": ["Keep current microservice topology"],
                "tradeoffs": ["Less independent scaling for lower cognitive and SRE overhead"],
                "assumptions": ["service_ownership_coverage > 0.8"],
                "risks": ["Monolith boundaries can erode without governance"],
                "tags": ["architecture", "incident-response"],
                "component": "backend-core",
                "decision_type": "architecture",
            },
            {
                "title": "Reject Redis queues for exactly-once settlement workflow",
                "summary": "Settlement path requires stronger delivery guarantees after reconciliation incidents.",
                "owners": ["Payments Platform"],
                "alternatives": ["Redis", "Kafka"],
                "tradeoffs": ["Higher ops overhead accepted for stricter guarantees"],
                "assumptions": ["settlement_duplicate_rate < 0.005"],
                "risks": ["Longer lead time for queue operations"],
                "tags": ["payments", "queues"],
                "component": "settlement",
                "decision_type": "architecture",
            },
        ]

        inserted: list[Decision] = []
        for idx, row in enumerate(samples, start=1):
            ev = Evidence(
                id=f"ev_demo_{idx}_{uuid.uuid4().hex[:6]}",
                source_type="demo",
                source_id=f"seed-{idx}",
                excerpt=row["summary"],
                url=None,
                content_hash=f"demo-{idx}",
            )
            decision = Decision(
                id=f"dec_demo_{idx}_{uuid.uuid4().hex[:6]}",
                title=row["title"],
                summary=row["summary"],
                date=str(date.today()),
                owners=row["owners"],
                alternatives=row["alternatives"],
                tradeoffs=row["tradeoffs"],
                assumptions=row["assumptions"],
                risks=row["risks"],
                consequences=[],
                evidence_ids=[ev.id],
                tags=row["tags"],
                component=row.get("component"),
                decision_type=row.get("decision_type", "technical"),
                confidence=0.82,
                updated_at=utc_now_iso(),
            )
            self.store.upsert(decision, [ev])
            inserted.append(decision)

        self.store.set_metric("queue_volume", 120000.0, "events/day")
        self.store.set_metric("payment_retry_error_rate", 0.042, "ratio")
        self.store.set_metric("service_ownership_coverage", 0.55, "ratio")
        self.store.set_metric("settlement_duplicate_rate", 0.002, "ratio")
        return inserted
