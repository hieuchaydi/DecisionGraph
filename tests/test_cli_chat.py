from __future__ import annotations

from pathlib import Path

from decisiongraph.cli_commands.core import process_chat_turn
from decisiongraph.service import DecisionGraphService
from decisiongraph.store import DecisionStore


def _service(tmp_path: Path) -> DecisionGraphService:
    svc = DecisionGraphService(DecisionStore(tmp_path / "dg.json"))
    svc.seed_demo()
    return svc


def test_chat_turn_query(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "Why did we choose Redis over RabbitMQ?")
    assert should_exit is False
    assert any("Decision:" in line for line in lines)
    assert any("Confidence:" in line for line in lines)


def test_chat_turn_list_with_limit(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "/list 2")
    assert should_exit is False
    assert len(lines) == 2


def test_chat_turn_guardrail(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "/guard Change payment retry logic")
    assert should_exit is False
    assert lines
    assert '"blocked"' in lines[0]


def test_chat_turn_find(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "/find rabbitmq")
    assert should_exit is False
    assert lines
    assert any("rabbitmq" in line.lower() for line in lines)


def test_chat_turn_supersede(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    old = next(row for row in svc.list_decisions(limit=100) if row.title == "Cap payment retries at 2 attempts")
    new = svc.ingest_text(
        source_id="chat-supersede",
        source_type="rfc",
        text=(
            "Title: Keep payment retry cap at 2 attempts with stronger auditing\n"
            "Summary: we keep retry cap at 2 and add audit visibility."
        ),
    )

    should_exit, lines = process_chat_turn(svc, f"/supersede {new.id} {old.id}")
    assert should_exit is False
    assert "Supersede link updated" in lines[0]


def test_chat_turn_watch(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "/watch")
    assert should_exit is False
    assert lines
    assert '"alerts"' in lines[0]


def test_chat_turn_exit(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "/exit")
    assert should_exit is True
    assert lines == ["Bye."]


def test_chat_turn_unknown_slash_command(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    should_exit, lines = process_chat_turn(svc, "/not-a-command")
    assert should_exit is False
    assert "Unknown command" in lines[0]
