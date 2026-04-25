from __future__ import annotations

import re
import uuid
from datetime import date

from decisiongraph.models import Decision, Evidence


def _first_sentence(text: str, fallback: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return fallback
    pieces = re.split(r"[.!?]", cleaned)
    sentence = pieces[0].strip()
    return sentence[:140] if sentence else fallback


def _extract_list(text: str, prefixes: list[str]) -> list[str]:
    out: list[str] = []
    lines = text.splitlines()
    for line in lines:
        lower = line.lower().strip()
        for pref in prefixes:
            if lower.startswith(pref):
                value = line.split(":", 1)[1].strip() if ":" in line else line.strip()
                if value:
                    out.append(value)
    return out


def _extract_from_heading_block(text: str, heading_names: list[str]) -> list[str]:
    lines = text.splitlines()
    current: str | None = None
    buckets: dict[str, list[str]] = {}
    names = {name.lower() for name in heading_names}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip().lower()
            current = heading if heading in names else None
            if current and current not in buckets:
                buckets[current] = []
            continue
        if current is None:
            continue
        value = line
        if line.startswith("- "):
            value = line[2:].strip()
        if line.startswith("* "):
            value = line[2:].strip()
        if value:
            buckets.setdefault(current, []).append(value)
    out: list[str] = []
    for heading in heading_names:
        out.extend(buckets.get(heading.lower(), []))
    return out


def _extract_key_value(text: str, keys: list[str]) -> str | None:
    lines = text.splitlines()
    key_set = {k.lower() for k in keys}
    for raw in lines:
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() in key_set:
            val = value.strip()
            if val:
                return val
    return None


class HeuristicExtractor:
    def extract(self, text: str, source_type: str, source_id: str, url: str | None = None) -> tuple[Decision, Evidence]:
        ev_id = f"ev_{uuid.uuid4().hex[:10]}"
        dc_id = f"dec_{uuid.uuid4().hex[:10]}"
        excerpt = text[:600]
        evidence = Evidence(
            id=ev_id,
            source_type=source_type,
            source_id=source_id,
            excerpt=excerpt,
            url=url,
        )

        title = _extract_key_value(text, ["title", "decision", "decision title"]) or _first_sentence(
            text, "Decision extracted from source"
        )
        summary = _extract_key_value(text, ["summary", "context"]) or _first_sentence(text, title)
        date_value = _extract_key_value(text, ["date"]) or str(date.today())
        component = _extract_key_value(text, ["component", "module", "system area"])
        decision_type = _extract_key_value(text, ["decision type", "type"]) or "technical"

        alternatives = _extract_list(text, ["alternatives:", "rejected:", "considered:"])
        alternatives.extend(_extract_from_heading_block(text, ["alternatives", "rejected options"]))
        tradeoffs = _extract_list(text, ["tradeoff:", "trade-offs:", "tradeoff accepted:", "accepted tradeoff:"])
        tradeoffs.extend(_extract_from_heading_block(text, ["trade-offs", "tradeoffs"]))
        assumptions = _extract_list(text, ["assumption:", "assumptions:", "follow-up assumption:"])
        assumptions.extend(_extract_from_heading_block(text, ["assumptions"]))
        risks = _extract_list(text, ["risk:", "risks:", "unresolved risk:"])
        risks.extend(_extract_from_heading_block(text, ["risks", "unresolved risks"]))
        owners = _extract_list(text, ["owner:", "owners:", "proposer:"])
        owners.extend(_extract_from_heading_block(text, ["owners", "approvers"]))
        tags = _extract_list(text, ["tags:", "tag:"])
        consequences = _extract_from_heading_block(text, ["consequences", "downstream consequences"])

        decision = Decision(
            id=dc_id,
            title=title,
            summary=summary,
            date=date_value,
            owners=list(dict.fromkeys(owners)),
            alternatives=list(dict.fromkeys(alternatives)),
            tradeoffs=list(dict.fromkeys(tradeoffs)),
            assumptions=list(dict.fromkeys(assumptions)),
            risks=list(dict.fromkeys(risks)),
            consequences=list(dict.fromkeys(consequences)),
            evidence_ids=[evidence.id],
            tags=list(dict.fromkeys(tags + ["auto-extracted"])),
            component=component,
            decision_type=decision_type,
            confidence=0.62,
        )
        return decision, evidence
