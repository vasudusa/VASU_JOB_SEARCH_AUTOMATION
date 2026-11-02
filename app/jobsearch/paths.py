from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def resolve_root(path: str | Path | None = None) -> Path:
    if path is None:
        return ROOT
    return Path(path).resolve()


def rel(root: Path, *parts: str) -> Path:
    return root.joinpath(*parts)

