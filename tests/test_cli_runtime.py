from __future__ import annotations

from decisiongraph.cli_commands import runtime


def test_should_seed_demo_uses_cli_flag(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "auto_seed_demo", lambda: False)
    assert runtime._should_seed_demo(True) is True


def test_should_seed_demo_uses_env_when_cli_off(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "auto_seed_demo", lambda: True)
    assert runtime._should_seed_demo(False) is True


def test_seed_demo_if_needed_disabled(monkeypatch) -> None:
    called = {"seed": False}

    class DummyService:
        def seed_demo(self):
            called["seed"] = True
            return [1, 2, 3]

    monkeypatch.setattr(runtime, "build_service", lambda: DummyService())
    assert runtime._seed_demo_if_needed(False) == 0
    assert called["seed"] is False


def test_seed_demo_if_needed_enabled(monkeypatch) -> None:
    class DummyService:
        def seed_demo(self):
            return [1, 2, 3, 4]

    monkeypatch.setattr(runtime, "build_service", lambda: DummyService())
    assert runtime._seed_demo_if_needed(True) == 4
