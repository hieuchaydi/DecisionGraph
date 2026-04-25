from __future__ import annotations

from pathlib import Path

import typer

from decisiongraph.config import github_base_url, github_token
from decisiongraph.cli_commands.service_factory import build_service


def register_ingestion_commands(app: typer.Typer) -> None:
    @app.command('ingest')
    def ingest_file(
        source: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help='Text/Markdown file'),
        source_id: str = typer.Option('file-ingest', help='Source identifier'),
        source_type: str = typer.Option('note', help='Source type'),
    ) -> None:
        service = build_service()
        text = source.read_text(encoding='utf-8')
        decision = service.ingest_text(source_id=source_id, text=text, source_type=source_type)
        typer.echo(f'Ingested decision: {decision.id} | {decision.title}')

    @app.command('ingest-text')
    def ingest_text(
        source_id: str = typer.Option(..., help='Source identifier'),
        text: str = typer.Option(..., help='Reasoning text to ingest'),
        source_type: str = typer.Option('note', help='Source type'),
    ) -> None:
        service = build_service()
        decision = service.ingest_text(source_id=source_id, text=text, source_type=source_type)
        typer.echo(f'Ingested decision: {decision.id} | {decision.title}')

    @app.command('ingest-dir')
    def ingest_directory(
        directory: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, help='Directory to scan'),
        pattern: str = typer.Option('*.md', help='Glob pattern (recursive)'),
        source_type: str = typer.Option('doc', help='Source type'),
    ) -> None:
        service = build_service()
        rows = service.ingest_directory(directory=directory, pattern=pattern, source_type=source_type)
        typer.echo(f'Ingested {len(rows)} decisions from {directory}')

    @app.command('ingest-git')
    def ingest_git(
        repo: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, help='Git repository path'),
        max_commits: int = typer.Option(200, min=1, max=5000, help='Max commits to scan'),
        ref: str = typer.Option('HEAD', help='Git ref (branch/tag/sha)'),
    ) -> None:
        service = build_service()
        rows = service.ingest_git_history(repo_path=repo, max_commits=max_commits, ref=ref)
        typer.echo(f'Ingested {len(rows)} decisions from git history: {repo}')

    @app.command('ingest-jsonl')
    def ingest_jsonl(
        source: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help='JSONL file path'),
        source_type: str = typer.Option('external', help='Default source type'),
    ) -> None:
        service = build_service()
        rows = service.ingest_jsonl(path=source, default_source_type=source_type)
        typer.echo(f'Ingested {len(rows)} decisions from JSONL: {source}')

    @app.command('ingest-github')
    def ingest_github(
        owner: str = typer.Option(..., help='GitHub owner/org'),
        repo: str = typer.Option(..., help='GitHub repository name'),
        max_prs: int = typer.Option(100, min=0, max=2000, help='Max PRs to ingest'),
        max_issues: int = typer.Option(100, min=0, max=2000, help='Max issues to ingest'),
        state: str = typer.Option('all', help='Issue/PR state: open|closed|all'),
    ) -> None:
        service = build_service()
        rows = service.ingest_github(
            owner=owner,
            repo=repo,
            max_prs=max_prs,
            max_issues=max_issues,
            state=state,
            token=github_token(),
            base_url=github_base_url(),
        )
        typer.echo(f'Ingested {len(rows)} decisions from GitHub repo: {owner}/{repo}')

    @app.command('ingest-slack-export')
    def ingest_slack_export(
        export_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, help='Slack export folder'),
        max_messages: int = typer.Option(1000, min=1, max=50000, help='Max decision-like messages to ingest'),
    ) -> None:
        service = build_service()
        rows = service.ingest_slack_export(export_dir=export_dir, max_messages=max_messages)
        typer.echo(f'Ingested {len(rows)} decisions from Slack export: {export_dir}')

    @app.command('ingest-jira-json')
    def ingest_jira_json(
        source: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help='Jira export JSON path'),
    ) -> None:
        service = build_service()
        rows = service.ingest_jira_json(path=source)
        typer.echo(f'Ingested {len(rows)} decisions from Jira JSON: {source}')
