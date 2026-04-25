from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from decisiongraph.config import alert_webhook_for_target, governance_mode, governance_required_fields
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
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}
VALID_SEVERITIES = set(SEVERITY_RANK.keys())
ALERT_TARGETS = {"webhook", "slack", "discord", "teams"}


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
    if decision.superseded_by:
        # Keep superseded records searchable, but prefer active decisions.
        score -= 1.5
    if decision.supersedes:
        score += 0.15
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


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


class DecisionGraphService:
    def __init__(self, store: DecisionStore, extractor: HeuristicExtractor | None = None):
        self.store = store
        self.extractor = extractor or HeuristicExtractor()

    def _audit(self, event: str, payload: dict[str, Any]) -> None:
        self.store.append_audit_log(
            {
                "id": f"audit_{uuid.uuid4().hex[:12]}",
                "event": event,
                "ts": utc_now_iso(),
                "payload": payload,
            }
        )

    @staticmethod
    def _missing_governance_fields(decision: Decision, required_fields: list[str]) -> list[str]:
        missing: list[str] = []
        for field_name in required_fields:
            value = getattr(decision, field_name, None)
            if isinstance(value, list):
                if not any(str(item).strip() for item in value):
                    missing.append(field_name)
                continue
            if value is None or not str(value).strip():
                missing.append(field_name)
        return missing

    def _enforce_governance(self, decision: Decision, source_id: str, source_type: str) -> None:
        mode = governance_mode()
        if mode == "off":
            return

        required = governance_required_fields()
        missing = self._missing_governance_fields(decision, required)
        if not missing:
            return

        details = {
            "decision_id": decision.id,
            "source_id": source_id,
            "source_type": source_type,
            "missing_fields": missing,
            "mode": mode,
        }
        self._audit("governance.validation_failed", details)
        if mode == "strict":
            missing_csv = ", ".join(missing)
            raise ValueError(f"Governance validation failed. Missing fields: {missing_csv}")

    def ingest_text(self, source_id: str, text: str, source_type: str = "note", url: str | None = None) -> Decision:
        content_hash = _hash_text(text)
        existing_evidence = self.store.find_evidence(source_type=source_type, source_id=source_id, content_hash=content_hash)
        if existing_evidence:
            linked = self.store.find_decision_by_evidence(existing_evidence.id)
            if linked:
                self._audit(
                    "ingest.duplicate",
                    {
                        "source_id": source_id,
                        "source_type": source_type,
                        "decision_id": linked.id,
                        "evidence_id": existing_evidence.id,
                    },
                )
                return linked

        decision, evidence = self.extractor.extract(text=text, source_type=source_type, source_id=source_id, url=url)
        self._enforce_governance(decision, source_id=source_id, source_type=source_type)
        evidence.content_hash = content_hash
        self.store.upsert(decision, [evidence])
        self._audit(
            "ingest.created",
            {
                "source_id": source_id,
                "source_type": source_type,
                "decision_id": decision.id,
                "evidence_id": evidence.id,
            },
        )
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

    def list_audit_logs(self, limit: int = 100, event_type: str | None = None) -> list[dict[str, Any]]:
        return self.store.list_audit_logs(limit=limit, event_type=event_type)

    def supersede_decision(self, decision_id: str, superseded_decision_id: str) -> Decision:
        decision = self.store.get_decision(decision_id)
        if not decision:
            raise ValueError(f"Decision not found: {decision_id}")
        superseded = self.store.get_decision(superseded_decision_id)
        if not superseded:
            raise ValueError(f"Decision not found: {superseded_decision_id}")
        if decision.id == superseded.id:
            raise ValueError("A decision cannot supersede itself")
        if superseded.superseded_by and superseded.superseded_by != decision.id:
            raise ValueError(
                f"Decision {superseded.id} is already superseded by {superseded.superseded_by}"
            )

        if superseded.id not in decision.supersedes:
            decision.supersedes.append(superseded.id)
        superseded.superseded_by = decision.id
        now = utc_now_iso()
        decision.updated_at = now
        superseded.updated_at = now
        self.store.upsert(decision, [])
        self.store.upsert(superseded, [])
        self._audit(
            "decision.supersede",
            {
                "decision_id": decision.id,
                "superseded_decision_id": superseded.id,
            },
        )
        return decision

    @staticmethod
    def _union_values(*groups: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group:
                value = item.strip()
                if not value:
                    continue
                key = value.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(value)
        return out

    def merge_decisions(self, primary_decision_id: str, duplicate_decision_id: str, note: str = "") -> Decision:
        primary = self.store.get_decision(primary_decision_id)
        if not primary:
            raise ValueError(f"Decision not found: {primary_decision_id}")
        duplicate = self.store.get_decision(duplicate_decision_id)
        if not duplicate:
            raise ValueError(f"Decision not found: {duplicate_decision_id}")
        if primary.id == duplicate.id:
            raise ValueError("Cannot merge the same decision")
        if duplicate.superseded_by and duplicate.superseded_by != primary.id:
            raise ValueError(
                f"Duplicate decision {duplicate.id} is already superseded by {duplicate.superseded_by}"
            )

        primary.owners = self._union_values(primary.owners, duplicate.owners)
        primary.alternatives = self._union_values(primary.alternatives, duplicate.alternatives)
        primary.tradeoffs = self._union_values(primary.tradeoffs, duplicate.tradeoffs)
        primary.assumptions = self._union_values(primary.assumptions, duplicate.assumptions)
        primary.risks = self._union_values(primary.risks, duplicate.risks)
        primary.consequences = self._union_values(primary.consequences, duplicate.consequences)
        primary.tags = self._union_values(primary.tags, duplicate.tags, ["merged"])
        primary.evidence_ids = self._union_values(primary.evidence_ids, duplicate.evidence_ids)
        merged_supersedes = [entry for entry in duplicate.supersedes if entry != primary.id]
        primary.supersedes = self._union_values(primary.supersedes, merged_supersedes, [duplicate.id])
        primary.confidence = round(max(primary.confidence, duplicate.confidence), 3)
        if not primary.component and duplicate.component:
            primary.component = duplicate.component
        if not primary.summary and duplicate.summary:
            primary.summary = duplicate.summary
        if note.strip():
            primary.consequences = self._union_values(primary.consequences, [f"Merge note: {note.strip()}"])

        duplicate.superseded_by = primary.id
        duplicate.tags = self._union_values(duplicate.tags, ["merged-duplicate"])
        now = utc_now_iso()
        primary.updated_at = now
        duplicate.updated_at = now

        self.store.upsert(primary, [])
        self.store.upsert(duplicate, [])

        # Repoint downstream supersede links from duplicate -> primary.
        decisions = self.store.list_decisions(limit=10000)
        for item in decisions:
            if item.id in {primary.id, duplicate.id}:
                continue
            if duplicate.id not in item.supersedes:
                continue
            item.supersedes = [primary.id if entry == duplicate.id else entry for entry in item.supersedes]
            item.supersedes = self._union_values(item.supersedes)
            item.updated_at = now
            self.store.upsert(item, [])

        self._audit(
            "decision.merge",
            {
                "primary_decision_id": primary.id,
                "duplicate_decision_id": duplicate.id,
                "note": note.strip() or None,
            },
        )
        return primary

    def decision_timeline(
        self,
        *,
        limit: int = 200,
        component: str | None = None,
        tag: str | None = None,
        owner: str | None = None,
        decision_type: str | None = None,
        include_superseded: bool = True,
    ) -> dict[str, Any]:
        decisions = self.list_decisions(
            limit=10000,
            tag=tag,
            component=component,
            owner=owner,
            decision_type=decision_type,
        )
        if not include_superseded:
            decisions = [item for item in decisions if not item.superseded_by]

        def _timeline_sort_key(item: Decision) -> tuple[str, str]:
            day = (_parse_iso_date(item.date) or date(1970, 1, 1)).isoformat()
            return (day, item.updated_at)

        ordered = sorted(decisions, key=_timeline_sort_key)[:limit]
        events: list[dict[str, Any]] = []
        for idx, item in enumerate(ordered, start=1):
            events.append(
                {
                    "index": idx,
                    "decision_id": item.id,
                    "date": item.date,
                    "title": item.title,
                    "component": item.component,
                    "decision_type": item.decision_type,
                    "owners": item.owners,
                    "tags": item.tags,
                    "supersedes": item.supersedes,
                    "superseded_by": item.superseded_by,
                }
            )
        return {"count": len(events), "items": events}

    def evidence_quality_report(
        self,
        *,
        limit: int = 200,
        weak_threshold: float = 0.45,
    ) -> dict[str, Any]:
        decisions = self.store.list_decisions(limit=10000)[:limit]
        evidence_map = self.store.get_evidence_map()
        today = datetime.now(timezone.utc).date()
        items: list[dict[str, Any]] = []
        weak_count = 0
        for item in decisions:
            linked = [evidence_map[eid] for eid in item.evidence_ids if eid in evidence_map]
            evidence_count = len(linked)
            with_url_count = sum(1 for ev in linked if (ev.url or "").strip())
            evidence_score = min(1.0, evidence_count / 3.0)
            url_score = (with_url_count / evidence_count) if evidence_count else 0.0

            parsed_date = _parse_iso_date(item.date)
            if parsed_date is None:
                recency_score = 0.4
            else:
                age_days = max(0, (today - parsed_date).days)
                if age_days <= 180:
                    recency_score = 1.0
                elif age_days <= 365:
                    recency_score = 0.75
                elif age_days <= 730:
                    recency_score = 0.45
                else:
                    recency_score = 0.2

            confidence_score = max(0.0, min(1.0, item.confidence))
            score = round(
                (0.45 * evidence_score) + (0.2 * url_score) + (0.2 * recency_score) + (0.15 * confidence_score),
                3,
            )
            reasons: list[str] = []
            if evidence_count == 0:
                reasons.append("no_evidence")
            elif evidence_count < 2:
                reasons.append("low_evidence_count")
            if url_score < 0.5:
                reasons.append("low_source_link_coverage")
            if recency_score <= 0.45:
                reasons.append("stale_decision_record")
            if score < weak_threshold:
                weak_count += 1
                reasons.append("below_threshold")
            items.append(
                {
                    "decision_id": item.id,
                    "title": item.title,
                    "score": score,
                    "evidence_count": evidence_count,
                    "with_url_count": with_url_count,
                    "recency_score": round(recency_score, 3),
                    "confidence_score": round(confidence_score, 3),
                    "reasons": reasons,
                }
            )

        items.sort(key=lambda row: row["score"])
        avg_score = round((sum(row["score"] for row in items) / len(items)), 3) if items else 0.0
        return {
            "count": len(items),
            "weak_count": weak_count,
            "weak_threshold": weak_threshold,
            "avg_score": avg_score,
            "items": items,
        }

    def list_metrics(self) -> list[MetricSnapshot]:
        return self.store.list_metrics()

    def set_metric(self, key: str, value: float, unit: str | None = None) -> MetricSnapshot:
        snapshot = self.store.set_metric(key=key, value=value, unit=unit)
        self._audit(
            "metric.set",
            {
                "key": key,
                "value": float(value),
                "unit": unit,
            },
        )
        return snapshot

    @staticmethod
    def _watch_key(item: StaleAssumption) -> str:
        return f"{item.decision_id}|{item.metric_key}|{item.assumption}"

    @staticmethod
    def _parse_severities(raw: list[str] | None, default: set[str]) -> set[str]:
        if not raw:
            return set(default)
        parsed = {entry.strip().lower() for entry in raw if entry and entry.strip()}
        unknown = parsed - VALID_SEVERITIES
        if unknown:
            unknown_list = ", ".join(sorted(unknown))
            raise ValueError(f"Invalid severity values: {unknown_list}")
        return parsed

    def _dispatch_watch_notification(self, webhook_url: str, payload: dict[str, Any]) -> tuple[bool, str | None]:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(webhook_url, json=payload)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network dependency
            return False, str(exc)
        return True, None

    def run_assumption_watch(
        self,
        *,
        warn_severities: list[str] | None = None,
        critical_severities: list[str] | None = None,
        notify: bool = False,
        webhook_url: str | None = None,
        notify_target: str = "webhook",
    ) -> dict[str, Any]:
        target = notify_target.strip().lower() or "webhook"
        if target not in ALERT_TARGETS:
            raise ValueError(f"Invalid notify_target: {notify_target}")
        resolved_webhook_url = (webhook_url or "").strip() or (alert_webhook_for_target(target) or "")
        if notify and not resolved_webhook_url:
            raise ValueError(
                "webhook_url is required when notify=true "
                "(or configure connector env for selected notify_target)"
            )
        warn_on = self._parse_severities(warn_severities, {"medium", "high"})
        critical_on = self._parse_severities(critical_severities, {"high"})
        stale = self.detect_stale_assumptions()
        stale_map = {self._watch_key(item): item for item in stale}

        previous_state = self.store.get_watch_state()
        alerts: list[dict[str, Any]] = []
        for key, item in stale_map.items():
            previous_severity = previous_state.get(key)
            current_severity = item.severity
            previous_rank = SEVERITY_RANK.get(previous_severity or "", 0)
            current_rank = SEVERITY_RANK[current_severity]
            escalated = previous_severity is not None and current_rank > previous_rank
            is_new = previous_severity is None
            if current_severity in critical_on:
                level = "critical"
            elif current_severity in warn_on:
                level = "warn"
            else:
                level = ""
            if not level:
                continue
            if not (is_new or escalated):
                continue
            alerts.append(
                {
                    "decision_id": item.decision_id,
                    "metric_key": item.metric_key,
                    "assumption": item.assumption,
                    "previous_severity": previous_severity,
                    "current_severity": current_severity,
                    "transition": f"{previous_severity or 'none'}->{current_severity}",
                    "level": level,
                    "is_new": is_new,
                    "is_escalation": escalated,
                }
            )

        resolved = sorted(set(previous_state.keys()) - set(stale_map.keys()))
        self.store.set_watch_state({key: item.severity for key, item in stale_map.items()})

        notification_url = resolved_webhook_url
        notification_attempted = notify and bool(notification_url)
        notification_sent = False
        notification_error: str | None = None
        if notification_attempted and alerts:
            notification_sent, notification_error = self._dispatch_watch_notification(
                notification_url,
                {
                    "event": "decisiongraph.assumption_watch",
                    "alert_count": len(alerts),
                    "critical_count": sum(1 for item in alerts if item["level"] == "critical"),
                    "warn_count": sum(1 for item in alerts if item["level"] == "warn"),
                    "alerts": alerts,
                    "target": target,
                },
            )

        self._audit(
            "assumption.watch_run",
            {
                "stale_count": len(stale),
                "alert_count": len(alerts),
                "resolved_count": len(resolved),
                "notify": notify,
                "notify_target": target,
                "notification_sent": notification_sent,
            },
        )

        return {
            "stale_count": len(stale),
            "warn_count": sum(1 for item in stale if item.severity in warn_on),
            "critical_count": sum(1 for item in stale if item.severity in critical_on),
            "alerts": alerts,
            "resolved_count": len(resolved),
            "resolved_items": resolved,
            "warn_severities": sorted(warn_on),
            "critical_severities": sorted(critical_on),
            "notification": {
                "attempted": notification_attempted,
                "sent": notification_sent,
                "target": target if notification_attempted else None,
                "url": notification_url if notification_attempted else None,
                "error": notification_error,
            },
        }

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
        if best.supersedes:
            answer_lines.append(f"Supersedes: {', '.join(best.supersedes)}")
        if best.superseded_by:
            answer_lines.append(f"Superseded by: {best.superseded_by}")
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
        if best.superseded_by:
            warnings.append("decision_superseded")

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
