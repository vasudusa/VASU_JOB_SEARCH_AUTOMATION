from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def load_settings(root: Path) -> dict[str, Any]:
    return load_json(root / "01_config" / "settings.json")


def load_truth_store(root: Path) -> dict[str, Any]:
    return load_json(root / "02_profile" / "truth_store.json")


def load_synthetic_jobs(root: Path) -> list[dict[str, Any]]:
    return load_json(root / "04_job_sources" / "synthetic_jobs.json")

