from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

from decisiongraph.models import Decision, Evidence, MetricSnapshot

LOCK_TIMEOUT_SECONDS = 10.0
LOCK_POLL_SECONDS = 0.05
STALE_LOCK_SECONDS = 60.0


class DecisionStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")
        self._thread_lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._empty_payload())

    @staticmethod
    def _empty_payload() -> dict[str, Any]:
        return {
            "schema_version": 4,
            "decisions": [],
            "evidence": [],
            "metrics": [],
            "watch_state": {},
            "audit_logs": [],
        }

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        with self._thread_lock:
            self._acquire_file_lock()
            try:
                yield
            finally:
                self._release_file_lock()

    def _acquire_file_lock(self) -> None:
        started = time.monotonic()
        while True:
            try:
                fd = os.open(str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self._is_stale_lock():
                    try:
                        self._lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass
                if time.monotonic() - started > LOCK_TIMEOUT_SECONDS:
                    raise TimeoutError(f"Timed out waiting for data lock: {self._lock_path}")
                time.sleep(LOCK_POLL_SECONDS)
                continue
            try:
                os.write(fd, f"{os.getpid()}".encode("utf-8"))
            finally:
                os.close(fd)
            return

    def _release_file_lock(self) -> None:
        try:
            self._lock_path.unlink()
        except FileNotFoundError:
            return

    def _is_stale_lock(self) -> bool:
        try:
            age = time.time() - self._lock_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age > STALE_LOCK_SECONDS

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        normalized = self._empty_payload()
        normalized["schema_version"] = data.get("schema_version", 1)
        normalized["decisions"] = data.get("decisions", [])
        normalized["evidence"] = data.get("evidence", [])
        normalized["metrics"] = data.get("metrics", [])
        raw_watch_state = data.get("watch_state", {})
        if isinstance(raw_watch_state, dict):
            normalized["watch_state"] = {
                str(key): str(value)
                for key, value in raw_watch_state.items()
                if value is not None
            }
        else:
            normalized["watch_state"] = {}
        raw_audit_logs = data.get("audit_logs", [])
        if isinstance(raw_audit_logs, list):
            normalized["audit_logs"] = [entry for entry in raw_audit_logs if isinstance(entry, dict)]
        else:
            normalized["audit_logs"] = []
        return normalized

    def _read(self) -> dict[str, Any]:
        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw or "{}")
        return self._normalize(data)

    def _write(self, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, indent=2, ensure_ascii=False)
        tmp_path = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.path)
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass

    def reset(self) -> None:
        with self._exclusive_lock():
            self._write(self._empty_payload())

    def list_decisions(self, limit: int = 50) -> list[Decision]:
        data = self._read()
        items = [Decision.from_dict(item) for item in data["decisions"]]
        items.sort(key=lambda row: row.updated_at, reverse=True)
        return items[:limit]

    def list_evidence(self) -> list[Evidence]:
        data = self._read()
        return [Evidence.from_dict(item) for item in data["evidence"]]

    def list_metrics(self) -> list[MetricSnapshot]:
        data = self._read()
        return [MetricSnapshot.from_dict(item) for item in data["metrics"]]

    def get_decision(self, decision_id: str) -> Decision | None:
        for item in self.list_decisions(limit=10000):
            if item.id == decision_id:
                return item
        return None

    def get_evidence_map(self) -> dict[str, Evidence]:
        return {item.id: item for item in self.list_evidence()}

    def find_evidence(self, source_type: str, source_id: str, content_hash: str | None = None) -> Evidence | None:
        for item in self.list_evidence():
            if item.source_type != source_type:
                continue
            if item.source_id != source_id:
                continue
            if content_hash and item.content_hash and item.content_hash != content_hash:
                continue
            return item
        return None

    def find_decision_by_evidence(self, evidence_id: str) -> Decision | None:
        for item in self.list_decisions(limit=10000):
            if evidence_id in item.evidence_ids:
                return item
        return None

    def set_metric(self, key: str, value: float, unit: str | None = None) -> MetricSnapshot:
        with self._exclusive_lock():
            data = self._read()
            metrics = [MetricSnapshot.from_dict(item) for item in data["metrics"]]
            snapshot = MetricSnapshot(key=key, value=float(value), unit=unit)

            replaced = False
            for idx, item in enumerate(metrics):
                if item.key == key:
                    metrics[idx] = snapshot
                    replaced = True
                    break
            if not replaced:
                metrics.append(snapshot)

            data["metrics"] = [item.to_dict() for item in metrics]
            self._write(data)
            return snapshot

    def upsert(self, decision: Decision, evidence: list[Evidence]) -> None:
        with self._exclusive_lock():
            data = self._read()

            decision_rows = data["decisions"]
            updated = False
            for idx, row in enumerate(decision_rows):
                if row["id"] == decision.id:
                    decision_rows[idx] = decision.to_dict()
                    updated = True
                    break
            if not updated:
                decision_rows.append(decision.to_dict())

            evidence_rows = data["evidence"]
            evidence_by_id = {item["id"]: item for item in evidence_rows}
            for ev in evidence:
                evidence_by_id[ev.id] = ev.to_dict()
            data["evidence"] = list(evidence_by_id.values())
            data["decisions"] = decision_rows
            self._write(data)

    def get_watch_state(self) -> dict[str, str]:
        data = self._read()
        raw = data.get("watch_state", {})
        if not isinstance(raw, dict):
            return {}
        return {str(key): str(value) for key, value in raw.items() if value is not None}

    def set_watch_state(self, state: dict[str, str]) -> None:
        with self._exclusive_lock():
            data = self._read()
            data["watch_state"] = {str(key): str(value) for key, value in state.items()}
            self._write(data)

    def list_audit_logs(self, limit: int = 100, event_type: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        rows = [dict(item) for item in data.get("audit_logs", []) if isinstance(item, dict)]
        if event_type:
            normalized = event_type.strip().lower()
            rows = [item for item in rows if str(item.get("event", "")).lower() == normalized]
        rows.sort(key=lambda item: str(item.get("ts", "")), reverse=True)
        return rows[:limit]

    def append_audit_log(self, entry: dict[str, Any]) -> None:
        with self._exclusive_lock():
            data = self._read()
            logs = [item for item in data.get("audit_logs", []) if isinstance(item, dict)]
            logs.append(dict(entry))
            data["audit_logs"] = logs[-5000:]
            self._write(data)
