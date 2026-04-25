from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3)


class IngestRequest(BaseModel):
    source_id: str = Field(min_length=1)
    text: str = Field(min_length=5)
    source_type: str = 'note'
    url: str | None = None


class IngestDirectoryRequest(BaseModel):
    directory: str = Field(min_length=1)
    pattern: str = '*.md'
    source_type: str = 'doc'


class GuardrailRequest(BaseModel):
    change_request: str = Field(min_length=5)
    limit: int = Field(default=3, ge=1, le=10)


class MetricUpsertRequest(BaseModel):
    key: str = Field(min_length=2)
    value: float
    unit: str | None = None


class GitIngestRequest(BaseModel):
    repo_path: str = Field(min_length=1)
    max_commits: int = Field(default=200, ge=1, le=5000)
    ref: str = 'HEAD'


class JsonlIngestRequest(BaseModel):
    path: str = Field(min_length=1)
    source_type: str = 'external'


class GitHubIngestRequest(BaseModel):
    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    max_prs: int = Field(default=100, ge=0, le=2000)
    max_issues: int = Field(default=100, ge=0, le=2000)
    state: str = Field(default='all', pattern='^(open|closed|all)$')


class SlackExportIngestRequest(BaseModel):
    export_dir: str = Field(min_length=1)
    max_messages: int = Field(default=1000, ge=1, le=50000)


class JiraJsonIngestRequest(BaseModel):
    path: str = Field(min_length=1)


class EvalDatasetRequest(BaseModel):
    path: str = Field(min_length=1)


class ResearchScoreRequest(BaseModel):
    pain_frequency: int = Field(ge=0, le=5)
    impact: int = Field(ge=0, le=5)
    ownership_urgency: int = Field(ge=0, le=5)
    workaround_weakness: int = Field(ge=0, le=5)
    budget_willingness: int = Field(ge=0, le=5)


class DesignPartnerProgressRequest(BaseModel):
    target_partners: int = Field(default=5, ge=1)
    current_partners: int = Field(default=0, ge=0)
    validated_queries_per_week: int = Field(default=0, ge=0)
    time_to_answer_reduction_pct: float = Field(default=0.0, ge=0.0)
