from __future__ import annotations

from pathlib import Path

import typer

from decisiongraph.ops import doctor, release_check, runbook, schema_info, security_audit
from decisiongraph.strategy import get_section, list_sections, search_sections
from decisiongraph.cli_commands.utils import echo_json


def register_strategy_ops_commands(app: typer.Typer) -> None:
    @app.command('strategy-list')
    def strategy_list() -> None:
        echo_json(list_sections())

    @app.command('strategy-show')
    def strategy_show(section: str) -> None:
        echo_json(get_section(section))

    @app.command('strategy-search')
    def strategy_search(query: str) -> None:
        echo_json(search_sections(query))

    @app.command('doctor')
    def doctor_cmd() -> None:
        echo_json(doctor())

    @app.command('runbook')
    def runbook_cmd() -> None:
        echo_json(runbook())

    @app.command('release-check')
    def release_check_cmd(
        project_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False, dir_okay=True),
    ) -> None:
        echo_json(release_check(project_root=project_root.resolve()))

    @app.command('security-audit')
    def security_audit_cmd() -> None:
        echo_json(security_audit())

    @app.command('schema-info')
    def schema_info_cmd() -> None:
        echo_json(schema_info())
