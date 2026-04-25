from __future__ import annotations

from decisiongraph.strategy import get_section, list_sections, search_sections


def test_strategy_sections_list_and_get() -> None:
    rows = list_sections()
    assert rows
    core = get_section("core_problem")
    assert core["title"]


def test_strategy_alias_and_search() -> None:
    pricing = get_section("pricing")
    assert pricing["id"] == "pricing_packaging"
    hits = search_sections("incident")
    assert hits

