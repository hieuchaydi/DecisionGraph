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
