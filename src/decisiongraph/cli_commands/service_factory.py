from __future__ import annotations

from decisiongraph.config import resolve_data_path
from decisiongraph.service import DecisionGraphService
from decisiongraph.store import DecisionStore


def build_service() -> DecisionGraphService:
    return DecisionGraphService(DecisionStore(resolve_data_path()))
