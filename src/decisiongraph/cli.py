from __future__ import annotations

import typer

from decisiongraph.cli_commands import (
    register_core_commands,
    register_ingestion_commands,
    register_insight_commands,
    register_runtime_commands,
    register_strategy_ops_commands,
)

app = typer.Typer(help='DecisionGraph CLI')

register_core_commands(app)
register_ingestion_commands(app)
register_insight_commands(app)
register_strategy_ops_commands(app)
register_runtime_commands(app)
