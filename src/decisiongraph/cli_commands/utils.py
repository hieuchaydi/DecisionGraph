from __future__ import annotations

import json

import typer


def echo_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2))
