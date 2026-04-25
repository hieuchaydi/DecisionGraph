from decisiongraph.cli_commands.core import register_core_commands
from decisiongraph.cli_commands.ingestion import register_ingestion_commands
from decisiongraph.cli_commands.insights import register_insight_commands
from decisiongraph.cli_commands.runtime import register_runtime_commands
from decisiongraph.cli_commands.strategy_ops import register_strategy_ops_commands

__all__ = [
    'register_core_commands',
    'register_ingestion_commands',
    'register_insight_commands',
    'register_runtime_commands',
    'register_strategy_ops_commands',
]
