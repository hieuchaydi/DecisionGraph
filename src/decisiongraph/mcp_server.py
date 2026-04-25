from __future__ import annotations

from decisiongraph.mcp_toolsets import (
    build_service,
    register_core_tools,
    register_ingestion_tools,
    register_insight_tools,
    register_strategy_ops_tools,
)


def create_mcp():
    from mcp.server.fastmcp import FastMCP

    service = build_service()
    mcp = FastMCP('DecisionGraph')

    register_core_tools(mcp, service)
    register_ingestion_tools(mcp, service)
    register_insight_tools(mcp, service)
    register_strategy_ops_tools(mcp, service)

    return mcp


def run_stdio() -> None:
    server = create_mcp()
    server.run()
