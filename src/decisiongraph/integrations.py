from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

@dataclass
class IngestDocument:
    source_id: str
    text: str
    source_type: str
    url: str | None = None


def _run_git(repo_path: Path, args: list[str]) -> str:
    cmd = ["git", "-C", str(repo_path), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or "unknown git error"
        raise RuntimeError(f"Git command failed: {msg}")
    return proc.stdout


def ingest_docs_from_git_history(repo_path: Path, max_commits: int = 200, ref: str = "HEAD") -> list[IngestDocument]:
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Invalid repository path: {repo_path}")
    marker_field = "\x1f"
    marker_row = "\x1e"
    pretty = f"%H{marker_field}%ad{marker_field}%an{marker_field}%s{marker_field}%b{marker_row}"
    output = _run_git(
        repo_path,
        ["log", ref, f"--max-count={max_commits}", "--date=short", f"--pretty=format:{pretty}"],
    )
    rows = output.split(marker_row)
    docs: list[IngestDocument] = []
    for raw_row in rows:
        row = raw_row.strip()
        if not row:
            continue
        parts = row.split(marker_field)
        if len(parts) < 5:
            continue
        commit_hash, commit_date, author, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4]
        body = body.strip()
        text_lines = [
            f"Title: {subject}",
            f"Summary: {subject}",
            f"Owner: {author}",
            f"Date: {commit_date}",
            "Tags: git,commit,history",
            f"Component: {guess_component_from_subject(subject)}",
        ]
        if body:
            text_lines.append("")
            text_lines.append("Context:")
            text_lines.append(body)
        docs.append(
            IngestDocument(
                source_id=commit_hash,
                source_type="git_commit",
                text="\n".join(text_lines),
                url=None,
            )
        )
    return docs


def ingest_docs_from_jsonl(path: Path, default_source_type: str = "external") -> list[IngestDocument]:
    if not path.exists() or not path.is_file():
        raise ValueError(f"Invalid JSONL path: {path}")
    docs: list[IngestDocument] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {lineno}: {exc}") from exc
        source_id = str(payload.get("source_id") or payload.get("id") or f"line-{lineno}")
        text = str(payload.get("text") or payload.get("body") or payload.get("content") or "").strip()
        if not text:
            continue
        source_type = str(payload.get("source_type") or default_source_type)
        url = payload.get("url")
        docs.append(IngestDocument(source_id=source_id, source_type=source_type, text=text, url=url))
    return docs


def _github_headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_get(client: httpx.Client, url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    response = client.get(url, params=params)
    if response.status_code >= 400:
        message = response.text.strip()[:200]
        raise RuntimeError(f"GitHub API request failed [{response.status_code}] {url}: {message}")
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected GitHub API response for {url}")
    return payload


def ingest_docs_from_github_repo(
    owner: str,
    repo: str,
    *,
    max_prs: int = 100,
    max_issues: int = 100,
    state: str = "all",
    token: str | None = None,
    base_url: str = "https://api.github.com",
) -> list[IngestDocument]:
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        raise ValueError("owner and repo are required")
    if state not in {"open", "closed", "all"}:
        raise ValueError("state must be one of: open, closed, all")
    if max_prs < 0 or max_issues < 0:
        raise ValueError("max_prs and max_issues must be >= 0")

    root = base_url.rstrip("/")
    pr_url = f"{root}/repos/{owner}/{repo}/pulls"
    issue_url = f"{root}/repos/{owner}/{repo}/issues"
    docs: list[IngestDocument] = []

    with httpx.Client(timeout=20.0, headers=_github_headers(token)) as client:
        if max_prs > 0:
            remaining = max_prs
            page = 1
            while remaining > 0:
                batch_size = min(100, remaining)
                rows = _github_get(client, pr_url, {"state": state, "per_page": batch_size, "page": page})
                if not rows:
                    break
                for row in rows:
                    pr_number = row.get("number")
                    title = str(row.get("title") or "").strip()
                    body = str(row.get("body") or "").strip()
                    user = (row.get("user") or {}).get("login", "unknown")
                    merged_at = row.get("merged_at")
                    labels = [str(item.get("name", "")).strip() for item in row.get("labels", []) if item.get("name")]
                    status = "merged" if merged_at else str(row.get("state") or "unknown")
                    lines = [
                        f"Title: PR #{pr_number} {title}",
                        f"Summary: {title or 'No title'}",
                        f"Owner: {user}",
                        f"Date: {str(row.get('updated_at') or row.get('created_at') or '')[:10]}",
                        f"Tags: github,pr,{status}",
                        f"Component: {guess_component_from_subject(title)}",
                    ]
                    if labels:
                        lines.append("Alternatives: " + ", ".join(labels))
                    if body:
                        lines.append("")
                        lines.append("Context:")
                        lines.append(body)
                    docs.append(
                        IngestDocument(
                            source_id=f"gh-pr-{owner}-{repo}-{pr_number}",
                            source_type="github_pr",
                            text="\n".join(lines),
                            url=row.get("html_url"),
                        )
                    )
                count = len(rows)
                remaining -= count
                page += 1
                if count < batch_size:
                    break

        if max_issues > 0:
            remaining = max_issues
            page = 1
            while remaining > 0:
                batch_size = min(100, remaining)
                rows = _github_get(client, issue_url, {"state": state, "per_page": batch_size, "page": page})
                if not rows:
                    break
                filtered: list[dict[str, Any]] = []
                for row in rows:
                    if "pull_request" in row:
                        continue
                    filtered.append(row)
                for row in filtered:
                    issue_number = row.get("number")
                    title = str(row.get("title") or "").strip()
                    body = str(row.get("body") or "").strip()
                    user = (row.get("user") or {}).get("login", "unknown")
                    labels = [str(item.get("name", "")).strip() for item in row.get("labels", []) if item.get("name")]
                    status = str(row.get("state") or "unknown")
                    lines = [
                        f"Title: Issue #{issue_number} {title}",
                        f"Summary: {title or 'No title'}",
                        f"Owner: {user}",
                        f"Date: {str(row.get('updated_at') or row.get('created_at') or '')[:10]}",
                        f"Tags: github,issue,{status}",
                        f"Component: {guess_component_from_subject(title)}",
                    ]
                    if labels:
                        lines.append("Risks: " + ", ".join(labels))
                    if body:
                        lines.append("")
                        lines.append("Context:")
                        lines.append(body)
                    docs.append(
                        IngestDocument(
                            source_id=f"gh-issue-{owner}-{repo}-{issue_number}",
                            source_type="github_issue",
                            text="\n".join(lines),
                            url=row.get("html_url"),
                        )
                    )
                count = len(filtered)
                remaining -= count
                page += 1
                if len(rows) < batch_size:
                    break
    return docs


def _safe_date_from_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        if "." in text:
            base = float(text)
            dt = datetime.fromtimestamp(base, tz=timezone.utc)
            return dt.date().isoformat()
        dt = datetime.fromtimestamp(float(text), tz=timezone.utc)
        return dt.date().isoformat()
    except (TypeError, ValueError):
        return ""


def _decision_like_message(text: str) -> bool:
    lower = text.lower()
    markers = [
        "we should",
        "we decided",
        "decision",
        "tradeoff",
        "revert",
        "rollback",
        "choose",
        "because",
        "instead of",
    ]
    return any(marker in lower for marker in markers)


def ingest_docs_from_slack_export(export_dir: Path, max_messages: int = 1000) -> list[IngestDocument]:
    if not export_dir.exists() or not export_dir.is_dir():
        raise ValueError(f"Invalid Slack export directory: {export_dir}")
    docs: list[IngestDocument] = []
    count = 0
    for file_path in sorted(export_dir.rglob("*.json")):
        rel = str(file_path.relative_to(export_dir)).replace("\\", "/")
        if rel.lower().endswith("users.json") or rel.lower().endswith("channels.json"):
            continue
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        channel = rel.split("/")[0] if "/" in rel else "general"
        for row in payload:
            if count >= max_messages:
                return docs
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            if not text or not _decision_like_message(text):
                continue
            ts = str(row.get("ts") or "")
            user = str(row.get("user") or "unknown")
            date = _safe_date_from_timestamp(ts)
            lines = [
                f"Title: Slack decision signal in #{channel}",
                f"Summary: {text[:120]}",
                f"Owner: {user}",
                f"Date: {date}",
                f"Tags: slack,chat,{channel}",
                f"Component: {guess_component_from_subject(text)}",
                "",
                "Context:",
                text,
            ]
            docs.append(
                IngestDocument(
                    source_id=f"slack-{channel}-{ts}",
                    source_type="slack_message",
                    text="\n".join(lines),
                    url=None,
                )
            )
            count += 1
    return docs


def ingest_docs_from_jira_json(path: Path) -> list[IngestDocument]:
    if not path.exists() or not path.is_file():
        raise ValueError(f"Invalid Jira JSON path: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid Jira JSON: {exc}") from exc

    rows = payload.get("issues") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Jira JSON must contain 'issues' array or top-level list")

    docs: list[IngestDocument] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or item.get("id") or "").strip()
        fields = item.get("fields") or {}
        if not key:
            continue
        summary = str(fields.get("summary") or item.get("summary") or "").strip()
        description = fields.get("description") or item.get("description") or ""
        if isinstance(description, dict):
            description = json.dumps(description, ensure_ascii=False)
        description = str(description).strip()
        assignee_obj = fields.get("assignee") or {}
        assignee = str(assignee_obj.get("displayName") or assignee_obj.get("name") or "unknown")
        updated = str(fields.get("updated") or fields.get("created") or "")[:10]
        labels = [str(x).strip() for x in (fields.get("labels") or []) if str(x).strip()]
        components = [str(x.get("name", "")).strip() for x in (fields.get("components") or []) if x.get("name")]
        component = components[0] if components else guess_component_from_subject(summary)

        lines = [
            f"Title: Jira {key} {summary}",
            f"Summary: {summary or 'No summary'}",
            f"Owner: {assignee}",
            f"Date: {updated}",
            "Tags: jira,issue",
            f"Component: {component}",
        ]
        if labels:
            lines.append("Risks: " + ", ".join(labels))
        if description:
            lines.append("")
            lines.append("Context:")
            lines.append(description)
        docs.append(
            IngestDocument(
                source_id=f"jira-{key}",
                source_type="jira_issue",
                text="\n".join(lines),
                url=None,
            )
        )
    return docs


def guess_component_from_subject(subject: str) -> str:
    lower = subject.lower()
    if "auth" in lower or "token" in lower or "oauth" in lower:
        return "auth"
    if "payment" in lower or "billing" in lower:
        return "payments"
    if "queue" in lower or "redis" in lower or "kafka" in lower:
        return "messaging"
    if "incident" in lower or "rollback" in lower or "revert" in lower:
        return "incident-response"
    if "deploy" in lower or "release" in lower:
        return "delivery"
    return "core"
