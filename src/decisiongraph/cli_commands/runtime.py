from __future__ import annotations

import typer


def register_runtime_commands(app: typer.Typer) -> None:
    @app.command('serve')
    def serve(
        host: str = typer.Option('127.0.0.1'),
        port: int = typer.Option(8000, min=1, max=65535),
    ) -> None:
        import uvicorn

        uvicorn.run('decisiongraph.api:app', host=host, port=port, reload=False)

    @app.command('mcp')
    def run_mcp() -> None:
        from decisiongraph.mcp_server import run_stdio

        run_stdio()
