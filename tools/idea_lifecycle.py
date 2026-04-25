from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ALLOWED_STATUS = {"pending", "in_progress", "done"}
DEFAULT_DB = Path("idea_backlog.json")


@dataclass
class IdeaItem:
    md_path: str
    status: str = "pending"
    code_refs: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "md_path": self.md_path,
            "status": self.status,
            "code_refs": self.code_refs,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "IdeaItem":
        return IdeaItem(
            md_path=str(data["md_path"]),
            status=str(data.get("status", "pending")),
            code_refs=[str(x) for x in data.get("code_refs", [])],
            notes=str(data.get("notes", "")),
        )


def _read_db(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"items": [], "deleted": []}
    payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    return {"items": payload.get("items", []), "deleted": payload.get("deleted", [])}


def _write_db(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _scan_markdown(root: Path) -> list[str]:
    ignored_prefixes = {".venv", "__pycache__", ".pytest_cache"}
    paths: list[str] = []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if rel in {"README.md", "00-index.md"}:
            # Keep README/index outside idea backlog.
            continue
        first_part = rel.split("/", 1)[0]
        if first_part in ignored_prefixes:
            continue
        paths.append(rel)
    return paths


def sync(root: Path, db_path: Path) -> None:
    payload = _read_db(db_path)
    items = {item["md_path"]: IdeaItem.from_dict(item) for item in payload["items"]}
    deleted = set(payload.get("deleted", []))

    discovered = _scan_markdown(root)
    for rel in discovered:
        if rel in deleted:
            continue
        if rel not in items:
            items[rel] = IdeaItem(md_path=rel)

    # Remove items whose md no longer exists and status is not done.
    existing = set(discovered)
    for rel in list(items.keys()):
        if rel not in existing and items[rel].status != "done":
            del items[rel]

    new_payload = {
        "items": [item.to_dict() for item in sorted(items.values(), key=lambda row: row.md_path)],
        "deleted": sorted(deleted),
    }
    _write_db(db_path, new_payload)
    print(f"Synced {len(new_payload['items'])} idea items.")


def mark(db_path: Path, md_path: str, status: str, code_refs: list[str], notes: str) -> None:
    if status not in ALLOWED_STATUS:
        raise ValueError(f"Invalid status: {status}")
    payload = _read_db(db_path)
    items = {item["md_path"]: IdeaItem.from_dict(item) for item in payload["items"]}
    if md_path not in items:
        items[md_path] = IdeaItem(md_path=md_path)
    row = items[md_path]
    row.status = status
    if code_refs:
        row.code_refs = code_refs
    if notes:
        row.notes = notes
    payload["items"] = [item.to_dict() for item in sorted(items.values(), key=lambda r: r.md_path)]
    _write_db(db_path, payload)
    print(f"Marked {md_path} => {status}")


def prune(root: Path, db_path: Path, apply: bool) -> None:
    payload = _read_db(db_path)
    items = [IdeaItem.from_dict(item) for item in payload["items"]]
    done_items = [item for item in items if item.status == "done"]
    if not done_items:
        print("No done items to prune.")
        return

    print("Done items:")
    for row in done_items:
        print(f"- {row.md_path}")
    if not apply:
        print("Dry run only. Use --apply to delete.")
        return

    deleted = set(payload.get("deleted", []))
    remaining: list[IdeaItem] = []
    for row in items:
        path = root / row.md_path
        if row.status == "done":
            if path.exists():
                path.unlink()
                print(f"Deleted: {row.md_path}")
            deleted.add(row.md_path)
        else:
            remaining.append(row)

    new_payload = {
        "items": [item.to_dict() for item in sorted(remaining, key=lambda r: r.md_path)],
        "deleted": sorted(deleted),
    }
    _write_db(db_path, new_payload)


def report(db_path: Path) -> None:
    payload = _read_db(db_path)
    items = [IdeaItem.from_dict(item) for item in payload["items"]]
    counts = {"pending": 0, "in_progress": 0, "done": 0}
    for row in items:
        counts[row.status] = counts.get(row.status, 0) + 1
    print(f"Total: {len(items)}")
    for key in ["pending", "in_progress", "done"]:
        print(f"{key}: {counts.get(key, 0)}")
    print(f"deleted: {len(payload.get('deleted', []))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage idea .md lifecycle and safe pruning.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to lifecycle database JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync", help="Sync .md files into backlog db")

    mark_parser = sub.add_parser("mark", help="Mark one idea status")
    mark_parser.add_argument("--file", required=True, help="Markdown path relative to root")
    mark_parser.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUS))
    mark_parser.add_argument("--code-ref", action="append", default=[], help="Code reference path (repeatable)")
    mark_parser.add_argument("--notes", default="", help="Implementation note")

    prune_parser = sub.add_parser("prune", help="Delete .md files marked done")
    prune_parser.add_argument("--apply", action="store_true", help="Actually delete files")

    sub.add_parser("report", help="Show current idea status summary")

    args = parser.parse_args()
    root = args.root.resolve()
    db = args.db if args.db.is_absolute() else (root / args.db)

    if args.cmd == "sync":
        sync(root=root, db_path=db)
        return
    if args.cmd == "mark":
        mark(
            db_path=db,
            md_path=args.file,
            status=args.status,
            code_refs=args.code_ref,
            notes=args.notes,
        )
        return
    if args.cmd == "prune":
        prune(root=root, db_path=db, apply=args.apply)
        return
    if args.cmd == "report":
        report(db_path=db)
        return


if __name__ == "__main__":
    main()
