from __future__ import annotations

import typer

from decisiongraph.cli_commands.service_factory import build_service
from decisiongraph.config import auto_seed_demo


def _should_seed_demo(cli_flag: bool) -> bool:
    return cli_flag or auto_seed_demo()


def _seed_demo_if_needed(seed_enabled: bool) -> int:
    if not seed_enabled:
        return 0
    service = build_service()
    rows = service.seed_demo()
    return len(rows)


def register_runtime_commands(app: typer.Typer) -> None:
    @app.command("serve")
    def serve(
        host: str = typer.Option("127.0.0.1"),
        port: int = typer.Option(8000, min=1, max=65535),
        seed_demo: bool = typer.Option(
            False,
            "--seed-demo/--no-seed-demo",
            help="Seed demo decisions before starting server",
        ),
    ) -> None:
        import uvicorn

        inserted = _seed_demo_if_needed(_should_seed_demo(seed_demo))
        if inserted:
            typer.echo(f"Auto-seeded {inserted} demo decisions.")

        uvicorn.run("decisiongraph.api:app", host=host, port=port, reload=False)

    @app.command("mcp")
    def run_mcp() -> None:
        from decisiongraph.mcp_server import run_stdio

        run_stdio()
