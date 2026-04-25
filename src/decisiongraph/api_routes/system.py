from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from decisiongraph.config import api_token, environment_name
from decisiongraph.api_home import HOME_HTML
from decisiongraph.service import DecisionGraphService


def create_system_router(service: DecisionGraphService) -> APIRouter:
    router = APIRouter()

    @router.get('/health')
    def health() -> dict[str, str]:
        mode = 'protected' if api_token() else 'open'
        return {'status': 'ok', 'env': environment_name(), 'mode': mode}

    @router.get('/api/report/summary')
    def report_summary(format: str = 'json') -> object:
        report = service.summary_report()
        if format == 'markdown':
            return HTMLResponse(content=f"<pre>{report['markdown']}</pre>")
        return report['json']

    @router.get('/', response_class=HTMLResponse)
    def home() -> str:
        return HOME_HTML

    return router
