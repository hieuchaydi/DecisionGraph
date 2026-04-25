from __future__ import annotations

from pathlib import Path

from decisiongraph.config import github_base_url, github_token
from decisiongraph.service import DecisionGraphService


def register_ingestion_tools(mcp, service: DecisionGraphService) -> None:
    @mcp.tool()
    def ingest_git(repo_path: str, max_commits: int = 200, ref: str = 'HEAD') -> list[dict]:
        """Ingest decision candidates from local git history."""
        rows = service.ingest_git_history(repo_path=Path(repo_path).expanduser().resolve(), max_commits=max_commits, ref=ref)
        return [row.to_dict() for row in rows]

    @mcp.tool()
    def ingest_jsonl(path: str, source_type: str = 'external') -> list[dict]:
        """Ingest decision candidates from JSONL exports."""
        rows = service.ingest_jsonl(path=Path(path).expanduser().resolve(), default_source_type=source_type)
        return [row.to_dict() for row in rows]

    @mcp.tool()
    def ingest_github(
        owner: str,
        repo: str,
        max_prs: int = 100,
        max_issues: int = 100,
        state: str = 'all',
    ) -> list[dict]:
        """Ingest decision candidates from GitHub pull requests and issues."""
        rows = service.ingest_github(
            owner=owner,
            repo=repo,
            max_prs=max_prs,
            max_issues=max_issues,
            state=state,
            token=github_token(),
            base_url=github_base_url(),
        )
        return [row.to_dict() for row in rows]

    @mcp.tool()
    def ingest_slack_export(export_dir: str, max_messages: int = 1000) -> list[dict]:
        """Ingest decision candidates from Slack export JSON files."""
        rows = service.ingest_slack_export(export_dir=Path(export_dir).expanduser().resolve(), max_messages=max_messages)
        return [row.to_dict() for row in rows]

    @mcp.tool()
    def ingest_jira_json(path: str) -> list[dict]:
        """Ingest decision candidates from Jira export JSON."""
        rows = service.ingest_jira_json(path=Path(path).expanduser().resolve())
        return [row.to_dict() for row in rows]
