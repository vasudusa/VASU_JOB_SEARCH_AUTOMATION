from __future__ import annotations

from collections import defaultdict
from typing import Any


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for job in jobs:
        groups[job["duplicate_hash"]].append(job)

    canonical_jobs: list[dict[str, Any]] = []
    duplicate_records: list[dict[str, Any]] = []

    for duplicate_hash, group in groups.items():
        sorted_group = sorted(
            group,
            key=lambda item: (
                item.get("source_priority", 99),
                item.get("date_posted") or "",
                item.get("job_url") or "",
            ),
        )
        canonical = dict(sorted_group[0])
        duplicates = sorted_group[1:]
        canonical["duplicate_count"] = len(duplicates)
        canonical["duplicate_sources"] = [item["source"] for item in duplicates]
        canonical_jobs.append(canonical)

        for duplicate in duplicates:
            duplicate_records.append(
                {
                    "duplicate_hash": duplicate_hash,
                    "canonical_external_job_id": canonical.get("external_job_id"),
                    "duplicate_external_job_id": duplicate.get("external_job_id"),
                    "canonical_source": canonical.get("source"),
                    "duplicate_source": duplicate.get("source"),
                    "reason": "same normalized company, title, and location",
                    "canonical": canonical,
                    "duplicate": duplicate,
                }
            )

    canonical_jobs.sort(key=lambda item: (item["company"], item["job_title"]))
    return canonical_jobs, duplicate_records

