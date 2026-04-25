from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from decisiongraph.config import github_base_url, github_token
from decisiongraph.api_schemas import (
    GitHubIngestRequest,
    GitIngestRequest,
    IngestDirectoryRequest,
    IngestRequest,
    JiraJsonIngestRequest,
    JsonlIngestRequest,
    SlackExportIngestRequest,
)
from decisiongraph.service import DecisionGraphService


def create_ingestion_router(service: DecisionGraphService) -> APIRouter:
    router = APIRouter()

    @router.post('/api/ingest')
    def ingest(payload: IngestRequest) -> dict[str, object]:
        try:
            decision = service.ingest_text(
                source_id=payload.source_id,
                text=payload.text,
                source_type=payload.source_type,
                url=payload.url,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'decision': decision.to_dict()}

    @router.post('/api/ingest/directory')
    def ingest_directory(payload: IngestDirectoryRequest) -> dict[str, object]:
        directory = Path(payload.directory).expanduser().resolve()
        if not directory.exists() or not directory.is_dir():
            raise HTTPException(status_code=400, detail='Invalid directory')
        rows = service.ingest_directory(directory=directory, pattern=payload.pattern, source_type=payload.source_type)
        return {'status': 'ok', 'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/ingest/git')
    def ingest_git(payload: GitIngestRequest) -> dict[str, object]:
        repo = Path(payload.repo_path).expanduser().resolve()
        try:
            rows = service.ingest_git_history(repo_path=repo, max_commits=payload.max_commits, ref=payload.ref)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/ingest/jsonl')
    def ingest_jsonl(payload: JsonlIngestRequest) -> dict[str, object]:
        path = Path(payload.path).expanduser().resolve()
        try:
            rows = service.ingest_jsonl(path=path, default_source_type=payload.source_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/ingest/github')
    def ingest_github(payload: GitHubIngestRequest) -> dict[str, object]:
        try:
            rows = service.ingest_github(
                owner=payload.owner,
                repo=payload.repo,
                max_prs=payload.max_prs,
                max_issues=payload.max_issues,
                state=payload.state,
                token=github_token(),
                base_url=github_base_url(),
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/ingest/slack-export')
    def ingest_slack_export(payload: SlackExportIngestRequest) -> dict[str, object]:
        export_dir = Path(payload.export_dir).expanduser().resolve()
        try:
            rows = service.ingest_slack_export(export_dir=export_dir, max_messages=payload.max_messages)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/ingest/jira-json')
    def ingest_jira_json(payload: JiraJsonIngestRequest) -> dict[str, object]:
        path = Path(payload.path).expanduser().resolve()
        try:
            rows = service.ingest_jira_json(path=path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'count': len(rows), 'items': [item.to_dict() for item in rows]}

    return router
