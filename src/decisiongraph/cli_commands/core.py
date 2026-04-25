from __future__ import annotations

import json
from pathlib import Path

import typer

from decisiongraph.cli_commands.service_factory import build_service
from decisiongraph.cli_commands.utils import echo_json
from decisiongraph.config import resolve_data_path
from decisiongraph.service import DecisionGraphService
from decisiongraph.store import DecisionStore

CHAT_HELP = """Commands:
  /help                              Show this help
  /list [limit]                      List latest decisions
  /find <query>                      Search decisions by text
  /get <decision_id>                 Show one decision as JSON
  /guard <change request>            Run guardrail check
  /contradictions                    Show detected contradictions
  /stale                             Show stale assumptions
  /metrics                           Show metric snapshots
  /graph                             Show graph node/edge counts
  /report [json|markdown]            Show summary report
  /exit                              Quit chat

Anything else is treated as a question for decision query.
"""


def _render_query(answer) -> list[str]:
    lines = [answer.answer, f"Confidence: {answer.confidence}"]
    if answer.warnings:
        lines.append("Warnings: " + ", ".join(answer.warnings))
    if answer.related:
        lines.append("Related:")
        for item in answer.related:
            lines.append(f"- {item.title}")
    return lines


def _render_list(rows) -> list[str]:
    if not rows:
        return ["No decisions found."]
    return [f"{idx}. [{row.id}] {row.title} ({row.date})" for idx, row in enumerate(rows, start=1)]


def process_chat_turn(
    service: DecisionGraphService,
    message: str,
    *,
    list_limit: int = 20,
    guardrail_limit: int = 3,
) -> tuple[bool, list[str]]:
    text = message.strip()
    if not text:
        return False, []

    lower = text.lower()
    if lower in {"exit", "quit", "/exit", "/quit"}:
        return True, ["Bye."]
    if lower in {"help", "/help", "/?"}:
        return False, CHAT_HELP.splitlines()

    if text.startswith("/"):
        command, _, arg = text.partition(" ")
        cmd = command.lower()
        arg = arg.strip()

        if cmd == "/list":
            limit = list_limit
            if arg:
                try:
                    limit = int(arg)
                except ValueError:
                    return False, [f"Invalid limit: {arg}"]
                if limit < 1 or limit > 200:
                    return False, ["Limit must be in range 1..200"]
            return False, _render_list(service.list_decisions(limit=limit))

        if cmd == "/find":
            if not arg:
                return False, ["Usage: /find <query>"]
            return False, _render_list(service.list_decisions(limit=list_limit, query=arg))

        if cmd == "/get":
            if not arg:
                return False, ["Usage: /get <decision_id>"]
            row = service.get_decision(arg)
            if not row:
                return False, ["Decision not found."]
            return False, [json.dumps(row.to_dict(), indent=2)]

        if cmd == "/guard":
            if not arg:
                return False, ["Usage: /guard <change request>"]
            payload = service.guardrail(change_request=arg, limit=guardrail_limit).to_dict()
            return False, [json.dumps(payload, indent=2)]

        if cmd == "/contradictions":
            rows = [item.to_dict() for item in service.detect_contradictions()]
            return False, [json.dumps(rows, indent=2)]

        if cmd == "/stale":
            rows = [item.to_dict() for item in service.detect_stale_assumptions()]
            return False, [json.dumps(rows, indent=2)]

        if cmd == "/metrics":
            rows = [item.to_dict() for item in service.list_metrics()]
            return False, [json.dumps(rows, indent=2)]

        if cmd == "/graph":
            payload = service.graph_snapshot()
            node_count = len(payload.get("nodes", []))
            edge_count = len(payload.get("edges", []))
            return False, [f"Graph snapshot: {node_count} nodes, {edge_count} edges"]

        if cmd == "/report":
            fmt = (arg or "markdown").strip().lower()
            payload = service.summary_report()
            if fmt == "json":
                return False, [json.dumps(payload["json"], indent=2)]
            if fmt == "markdown":
                return False, [str(payload["markdown"])]
            return False, ["Usage: /report [json|markdown]"]

        return False, [f"Unknown command: {command}. Type /help."]

    answer = service.query(text)
    return False, _render_query(answer)


def register_core_commands(app: typer.Typer) -> None:
    @app.command("init")
    def init_data(reset: bool = typer.Option(False, help="Reset existing data file to empty schema")) -> None:
        path = resolve_data_path()
        store = DecisionStore(path)
        if reset:
            store.reset()
            typer.echo(f"Reset store at: {path}")
            return
        typer.echo(f"Initialized store at: {path}")

    @app.command("seed-demo")
    def seed_demo() -> None:
        service = build_service()
        rows = service.seed_demo()
        typer.echo(f"Inserted {len(rows)} demo decisions.")

    @app.command("query")
    def query(question: str) -> None:
        service = build_service()
        answer = service.query(question)
        for line in _render_query(answer):
            typer.echo(line)

    @app.command("chat")
    def chat(
        list_limit: int = typer.Option(20, min=1, max=200, help="Default limit for /list"),
        guardrail_limit: int = typer.Option(3, min=1, max=10, help="Default limit for /guard"),
    ) -> None:
        service = build_service()
        typer.echo("DecisionGraph chat started. Type /help for commands, /exit to quit.")
        while True:
            try:
                user_input = input("decisiongraph> ")
            except EOFError:
                typer.echo("Bye.")
                break
            except KeyboardInterrupt:
                typer.echo("\nBye.")
                break

            should_exit, lines = process_chat_turn(
                service,
                user_input,
                list_limit=list_limit,
                guardrail_limit=guardrail_limit,
            )
            for line in lines:
                typer.echo(line)
            if should_exit:
                break

    @app.command("list")
    def list_decisions(
        limit: int = typer.Option(20, min=1, max=200),
        q: str = typer.Option("", help="Search query"),
        tag: str = typer.Option("", help="Tag filter (comma-separated)"),
        component: str = typer.Option("", help="Component filter"),
        owner: str = typer.Option("", help="Owner filter"),
        decision_type: str = typer.Option("", help="Decision type filter"),
    ) -> None:
        service = build_service()
        rows = service.list_decisions(
            limit=limit,
            query=q or None,
            tag=tag or None,
            component=component or None,
            owner=owner or None,
            decision_type=decision_type or None,
        )
        for line in _render_list(rows):
            typer.echo(line)

    @app.command("get")
    def get_decision(decision_id: str) -> None:
        service = build_service()
        row = service.get_decision(decision_id)
        if not row:
            typer.echo("Decision not found.")
            raise typer.Exit(code=1)
        echo_json(row.to_dict())

    @app.command("guardrail")
    def guardrail(change_request: str, limit: int = typer.Option(3, min=1, max=10)) -> None:
        service = build_service()
        result = service.guardrail(change_request=change_request, limit=limit)
        echo_json(result.to_dict())

    @app.command("contradictions")
    def contradictions() -> None:
        service = build_service()
        rows = service.detect_contradictions()
        echo_json([item.to_dict() for item in rows])

    @app.command("stale-assumptions")
    def stale_assumptions() -> None:
        service = build_service()
        rows = service.detect_stale_assumptions()
        echo_json([item.to_dict() for item in rows])

    @app.command("metric-set")
    def metric_set(
        key: str = typer.Option(..., help="Metric key"),
        value: float = typer.Option(..., help="Metric value"),
        unit: str = typer.Option("", help="Metric unit"),
    ) -> None:
        service = build_service()
        row = service.set_metric(key=key, value=value, unit=unit or None)
        echo_json(row.to_dict())

    @app.command("metrics")
    def metrics() -> None:
        service = build_service()
        rows = service.list_metrics()
        echo_json([item.to_dict() for item in rows])

    @app.command("graph")
    def graph() -> None:
        service = build_service()
        echo_json(service.graph_snapshot())

    @app.command("report")
    def report(
        format: str = typer.Option("markdown", help="markdown or json"),
        output: Path | None = typer.Option(None, help="Optional output file path"),
    ) -> None:
        service = build_service()
        payload = service.summary_report()
        fmt = format.strip().lower()
        if fmt == "json":
            content = json.dumps(payload["json"], indent=2)
        else:
            content = str(payload["markdown"])
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
            typer.echo(f"Wrote report to: {output}")
            return
        typer.echo(content)
