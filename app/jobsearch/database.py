from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def connect_database(root: Path, reset: bool = True) -> sqlite3.Connection:
    db_path = root / "05_database" / "job_search.sqlite"
    if reset and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    with (root / "05_database" / "schema.sql").open("r", encoding="utf-8") as handle:
        connection.executescript(handle.read())
    return connection


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def insert_event(connection: sqlite3.Connection, run_id: str, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
    connection.execute(
        "INSERT INTO events (run_id, event_time, event_type, message, metadata_json) VALUES (?, ?, ?, ?, ?)",
        (run_id, datetime.now().isoformat(timespec="seconds"), event_type, message, as_json(metadata or {})),
    )

