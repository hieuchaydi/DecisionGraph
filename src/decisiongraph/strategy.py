from __future__ import annotations

from typing import Any


SECTIONS: dict[str, dict[str, Any]] = {
    "core_problem": {
        "title": "Core Problem",
        "summary": "Software teams fail when decision memory is lost, not because code is impossible.",
        "points": [
            "Teams forget why architecture choices were made.",
            "Trade-offs and rejected options disappear from daily context.",
            "Operational incidents are not linked back to decision rationale.",
        ],
    },
    "hidden_cost": {
        "title": "Hidden Cost",
        "summary": "Lost decision context creates invisible but expensive engineering debt.",
        "points": [
            "Slower onboarding",
            "Repeated failed proposals",
            "Risky refactors",
            "Higher incident response time",
        ],
    },
    "why_now": {
        "title": "Why Now",
        "summary": "Team churn + fragmented tools + AI coding velocity increases memory loss risk.",
    },
    "product_vision": {
        "title": "Product Vision",
        "summary": "DecisionGraph is an engineering decision memory system that preserves why behind code.",
    },
    "north_star": {
        "title": "North Star",
        "summary": "Every high-impact change should be explainable with traceable decision history under 2 minutes.",
    },
    "user_stories": {
        "title": "User Stories",
        "points": [
            "Staff engineer checks historical incidents before risky refactor.",
            "Engineering manager inspects stale assumptions before sprint planning.",
            "CTO gets ownership/risk visibility across critical decisions.",
        ],
    },
    "oss_strategy": {
        "title": "OSS Strategy",
        "summary": "Use open-source ingestion/query core as wedge and monetize integrations + governance.",
        "free": ["Local ingestion", "Decision query", "Basic graph view"],
        "paid": ["Org-wide graph", "Policy guardrails", "Governance and audit"],
    },
    "pricing_packaging": {
        "title": "Pricing and Packaging",
        "tiers": [
            {"name": "Team", "focus": "core integrations + decision query"},
            {"name": "Business", "focus": "incident/deploy signals + advanced guardrails"},
            {"name": "Enterprise", "focus": "SSO, RBAC, audit, private deployment"},
        ],
    },
    "go_to_market": {
        "title": "Go-to-Market",
        "segments": ["Engineering teams 15-200 devs", "High incident pressure", "Active AI coding adoption"],
        "channels": ["OSS traction", "Design partner program", "Architecture communities"],
    },
    "moat": {
        "title": "Moat",
        "summary": "Long-lived org decision graph + integration depth + AI safety layer creates retention moat.",
    },
    "roadmap_30d": {
        "title": "MVP 30 Days",
        "weeks": [
            "Week 1: ingest + extraction + schema",
            "Week 2: timeline + evidence links + core queries",
            "Week 3: confidence + contradiction + dogfooding",
            "Week 4: OSS alpha + docs + design partner calls",
        ],
    },
    "roadmap_12m": {
        "title": "Roadmap 12 Months",
        "quarters": {
            "Q1": "OSS launch with git-first focus",
            "Q2": "Slack/Notion connectors + team workspace graph",
            "Q3": "AI guardrails + incident/deploy integration",
            "Q4": "Enterprise controls + policy engine",
        },
    },
    "risks_mitigations": {
        "title": "Risks and Mitigations",
        "items": [
            {"risk": "Low extraction quality", "mitigation": "Human feedback loops + confidence gates"},
            {"risk": "Noisy unstructured data", "mitigation": "Source ranking + schema constraints"},
            {"risk": "Security concerns", "mitigation": "Least privilege + private deployment options"},
            {"risk": "Perceived as nice-to-have", "mitigation": "Tie outcomes to incident/onboarding ROI"},
        ],
    },
    "pitch_1m": {
        "title": "1-Minute Pitch",
        "summary": "DecisionGraph preserves why behind code so teams move faster without repeating mistakes.",
    },
    "pitch_5m": {
        "title": "5-Minute Pitch",
        "outline": [
            "Problem: memory loss in engineering decisions",
            "Why current tools miss it",
            "Product and architecture",
            "Value outcomes",
            "Business model",
        ],
    },
    "investor_thesis": {
        "title": "Investor Thesis",
        "summary": "Institutional engineering memory is underbuilt and increasingly critical with AI coding acceleration.",
    },
    "enterprise_one_pager": {
        "title": "Enterprise One Pager",
        "buyer_group": ["CTO", "VP Engineering", "Platform Lead", "Security Lead"],
        "success_metrics": ["faster onboarding", "fewer repeated incidents", "lower risky AI changes"],
    },
    "glossary": {
        "title": "Glossary",
        "terms": {
            "decision_memory": "historical reasoning behind technical changes",
            "evidence": "artifact supporting a decision",
            "stale_assumption": "assumption invalid under current metrics",
            "confidence_score": "estimated reliability of generated answer",
        },
    },
    "competitor_map": {
        "title": "Competitor Map",
        "summary": "Coding assistants generate fast, RAG retrieves fast, DecisionGraph explains causality and intent.",
    },
    "decision_record_template": {
        "title": "Decision Record Template",
        "fields": [
            "Decision title",
            "Date",
            "Owner(s)",
            "Context",
            "Options considered",
            "Chosen option",
            "Rejected options and why",
            "Accepted trade-offs",
            "Assumptions",
            "Risk and mitigation",
            "Evidence links",
            "Review date",
        ],
    },
    "api_contract": {
        "title": "Sample API Contract",
        "endpoint": "POST /v1/query/why",
        "request": ["question", "repo_id", "time_range?"],
        "response": ["answer", "confidence", "decision_nodes", "evidence_links", "warnings"],
    },
    "customer_icp": {
        "title": "Ideal Customer Profile",
        "summary": "Teams 20-300 engineers with legacy complexity, incident pressure, and AI coding adoption.",
    },
    "persona_cto": {
        "title": "Persona CTO",
        "pain": "Limited visibility into why strategic technical debt exists.",
        "trigger": "Repeated incidents tied to lost context.",
    },
    "persona_engineering_manager": {
        "title": "Persona Engineering Manager",
        "pain": "Onboarding drag and repeated architecture debates.",
        "trigger": "Alignment cycles repeat every quarter.",
    },
    "persona_staff_engineer": {
        "title": "Persona Staff Engineer",
        "pain": "Risky legacy changes without rationale traceability.",
        "trigger": "Hidden business constraints break refactors.",
    },
    "security_model": {
        "title": "Security Model",
        "principles": [
            "Least privilege connector scopes",
            "Encryption in transit and at rest",
            "Tenant isolation",
            "Source provenance traceability",
        ],
    },
    "privacy": {
        "title": "Privacy",
        "items": [
            "Configurable retention",
            "Source-level access controls",
            "PII redaction for ingest pipelines",
            "Query/export audit logs",
        ],
    },
    "enterprise_requirements": {
        "title": "Enterprise Requirements",
        "checklist": [
            "SSO (SAML/OIDC)",
            "RBAC",
            "Audit export",
            "Data residency",
            "Retention policy controls",
            "Incident response SLA",
        ],
    },
}


ALIASES: dict[str, str] = {
    "problem": "core_problem",
    "vision": "product_vision",
    "pricing": "pricing_packaging",
    "gtm": "go_to_market",
    "one_pager": "enterprise_one_pager",
    "icp": "customer_icp",
    "persona_cto": "persona_cto",
    "persona_em": "persona_engineering_manager",
    "persona_staff": "persona_staff_engineer",
}


def list_sections() -> list[str]:
    return sorted(SECTIONS.keys())


def get_section(name: str) -> dict[str, Any]:
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key not in SECTIONS:
        raise ValueError(f"Unknown strategy section: {name}")
    return {"id": key, **SECTIONS[key]}


def search_sections(query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return [get_section(name) for name in list_sections()]
    rows: list[dict[str, Any]] = []
    for key in list_sections():
        payload = get_section(key)
        blob = str(payload).lower()
        if q in blob:
            rows.append(payload)
    return rows

