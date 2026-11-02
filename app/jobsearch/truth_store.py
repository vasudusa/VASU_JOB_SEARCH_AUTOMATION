from __future__ import annotations

from typing import Any


class TruthStore:
    def __init__(self, store: dict[str, Any]) -> None:
        self.store = store
        self.sources = {source["id"]: source for source in store.get("sources", [])}
        self.facts = {fact["id"]: fact for fact in store.get("facts", [])}

    def get(self, fact_id: str) -> dict[str, Any]:
        return self.facts[fact_id]

    def facts_for_ids(self, fact_ids: list[str]) -> list[dict[str, Any]]:
        return [self.facts[fact_id] for fact_id in fact_ids if fact_id in self.facts]

    def evidence_sources_for(self, fact_ids: list[str]) -> list[str]:
        source_ids: list[str] = []
        for fact in self.facts_for_ids(fact_ids):
            for source_id in fact.get("evidence_sources", []):
                if source_id not in source_ids:
                    source_ids.append(source_id)
        return source_ids

    def missing_required_sources(self) -> list[dict[str, Any]]:
        return [
            source
            for source in self.store.get("sources", [])
            if source.get("status") == "MISSING"
        ]

