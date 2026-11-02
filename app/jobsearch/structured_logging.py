from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class EventLogger:
    def __init__(self, root: Path, run_id: str) -> None:
        self.root = root
        self.run_id = run_id
        self.log_path = root / "08_logs" / f"phase1_{run_id}.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, message: str, **metadata: Any) -> None:
        event = {
            "run_id": self.run_id,
            "event_time": datetime.now().isoformat(timespec="seconds"),
            "event_type": event_type,
            "message": message,
            "metadata": metadata,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

