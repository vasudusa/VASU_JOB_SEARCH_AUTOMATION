from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any


SOURCE_PRIORITY = {
    "company_careers": 1,
    "company": 1,
    "linkedin_synthetic": 2,
    "job_board_synthetic": 3,
}


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title: str) -> str:
    title_norm = normalize_text(title)
    replacements = {
        "sr ": "senior ",
        "proj mgr": "project manager",
        "tpm": "technical project manager",
    }
    for old, new in replacements.items():
        title_norm = title_norm.replace(old, new)
    return re.sub(r"\s+", " ", title_norm).strip()


def duplicate_hash(company: str, title: str, location: str | None) -> str:
    fingerprint = "|".join(
        [
            normalize_text(company),
            normalize_title(title),
            normalize_text(location or ""),
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:20]


def normalize_job(raw: dict[str, Any], date_found: str | None = None) -> dict[str, Any]:
    title = raw.get("job_title") or raw.get("title") or ""
    company = raw.get("company") or ""
    location = raw.get("location") or ""
    normalized = {
        "source": raw.get("source", "unknown"),
        "source_priority": SOURCE_PRIORITY.get(raw.get("source", "unknown"), 99),
        "external_job_id": raw.get("external_job_id"),
        "company": company.strip(),
        "company_brand_score": int(raw.get("company_brand_score", 5)),
        "job_title": title.strip(),
        "normalized_title": normalize_title(title),
        "location": location.strip(),
        "country": (raw.get("country") or "").strip(),
        "work_mode": (raw.get("work_mode") or "").strip(),
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "currency": raw.get("currency"),
        "job_url": raw.get("job_url"),
        "source_url": raw.get("source_url"),
        "date_found": date_found or date.today().isoformat(),
        "date_posted": raw.get("date_posted"),
        "description": raw.get("description", ""),
        "requirements": list(raw.get("requirements", [])),
        "screening_questions": list(raw.get("screening_questions", [])),
        "simulated_site_flags": list(raw.get("simulated_site_flags", [])),
        "duplicate_hash": duplicate_hash(company, title, location),
        "raw": raw,
    }
    return normalized


def normalize_jobs(raw_jobs: list[dict[str, Any]], date_found: str | None = None) -> list[dict[str, Any]]:
    return [normalize_job(job, date_found=date_found) for job in raw_jobs]

