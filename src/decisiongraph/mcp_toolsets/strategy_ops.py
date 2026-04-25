from __future__ import annotations

from pathlib import Path

from decisiongraph.ops import doctor, release_check, runbook, schema_info, security_audit
from decisiongraph.service import DecisionGraphService
from decisiongraph.strategy import get_section, list_sections, search_sections


def register_strategy_ops_tools(mcp, service: DecisionGraphService) -> None:  # noqa: ARG001
    @mcp.tool()
    def strategy_sections() -> list[str]:
        """List available strategy sections."""
        return list_sections()

    @mcp.tool()
    def strategy_show(section_id: str) -> dict:
        """Return one strategy section by id."""
        return get_section(section_id)

    @mcp.tool()
    def strategy_search(query: str) -> list[dict]:
        """Search strategy sections by text."""
        return search_sections(query)

    @mcp.tool()
    def ops_doctor() -> dict:
        """Run local environment health checks."""
        return doctor()

    @mcp.tool()
    def ops_runbook() -> dict:
        """Return operational runbook playbook."""
        return runbook()

    @mcp.tool()
    def ops_release_check(project_root: str = '.') -> dict:
        """Run release readiness checks for workspace."""
        return release_check(project_root=Path(project_root).expanduser().resolve())

    @mcp.tool()
    def ops_security_audit() -> dict:
        """Return perimeter security configuration summary."""
        return security_audit()

    @mcp.tool()
    def schema_info_tool() -> dict:
        """Return active data schema info."""
        return schema_info()
