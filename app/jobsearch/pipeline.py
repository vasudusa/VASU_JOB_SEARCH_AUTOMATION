from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .application_engine import prepare_application
from .config import load_settings, load_synthetic_jobs, load_truth_store, write_json
from .database import as_json, connect_database, insert_event
from .deduplication import deduplicate_jobs
from .normalizer import normalize_jobs
from .question_engine import QuestionEngine
from .reporting import generate_daily_report
from .scoring import score_job
from .structured_logging import EventLogger
from .truth_store import TruthStore


def _insert_truth_facts(connection, truth_store: TruthStore) -> None:
    for fact in truth_store.store.get("facts", []):
        connection.execute(
            """
            INSERT OR REPLACE INTO truth_facts
            (fact_id, status, claim, value_json, evidence_sources_json, allowed_statement, forbidden_statements_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact["id"],
                fact["status"],
                fact["claim"],
                as_json(fact.get("value")),
                as_json(fact.get("evidence_sources", [])),
                fact.get("allowed_statement"),
                as_json(fact.get("forbidden_statements", [])),
            ),
        )


def _insert_resumes(connection, settings: dict[str, Any], root: Path) -> None:
    for key, resume in settings["resume_variants"].items():
        path = root / resume["path"]
        connection.execute(
            """
            INSERT OR REPLACE INTO resumes (variant_key, label, path, exists_on_disk, required)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, resume["label"], resume["path"], int(path.exists()), int(resume.get("required", False))),
        )


def _insert_job(connection, run_id: str, job: dict[str, Any], is_canonical: bool, canonical_job_id: int | None = None) -> int:
    cursor = connection.execute(
        """
        INSERT INTO jobs
        (run_id, source, external_job_id, company, job_title, normalized_title, location, country,
         work_mode, salary_min, salary_max, currency, job_url, source_url, date_found, date_posted,
         description, requirements_json, duplicate_hash, canonical_job_id, is_canonical, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            job["source"],
            job.get("external_job_id"),
            job["company"],
            job["job_title"],
            job["normalized_title"],
            job.get("location"),
            job.get("country"),
            job.get("work_mode"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("currency"),
            job.get("job_url"),
            job.get("source_url"),
            job["date_found"],
            job.get("date_posted"),
            job.get("description"),
            as_json(job.get("requirements", [])),
            job["duplicate_hash"],
            canonical_job_id,
            int(is_canonical),
            as_json(job.get("raw", job)),
        ),
    )
    return int(cursor.lastrowid)


def run_phase1(root: Path, reset_db: bool = True) -> dict[str, Any]:
    run_id = datetime.now().strftime("%Y-%m-%d")
    run_uuid = str(uuid.uuid4())
    settings = load_settings(root)
    truth_data = load_truth_store(root)
    truth_store = TruthStore(truth_data)
    question_engine = QuestionEngine(truth_store, settings)
    raw_jobs = load_synthetic_jobs(root)
    logger = EventLogger(root, run_id)
    logger.log("RUN_STARTED", "Phase 1 dry-run started.", run_uuid=run_uuid)

    connection = connect_database(root, reset=reset_db)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        "INSERT INTO config_snapshots (run_id, created_at, config_json) VALUES (?, ?, ?)",
        (run_id, datetime.now().isoformat(timespec="seconds"), as_json(settings)),
    )
    _insert_truth_facts(connection, truth_store)
    _insert_resumes(connection, settings, root)

    source_started = datetime.now().isoformat(timespec="seconds")
    normalized_jobs = normalize_jobs(raw_jobs)
    canonical_jobs, duplicate_records = deduplicate_jobs(normalized_jobs)
    connection.execute(
        """
        INSERT INTO source_runs
        (run_id, source_name, started_at, completed_at, records_found, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            "synthetic_jobs",
            source_started,
            datetime.now().isoformat(timespec="seconds"),
            len(raw_jobs),
            "COMPLETED",
            "Synthetic Phase 1 test jobs only.",
        ),
    )
    logger.log("JOBS_NORMALIZED", "Synthetic jobs normalized.", raw_jobs=len(raw_jobs), unique_jobs=len(canonical_jobs))
    insert_event(connection, run_id, "JOBS_NORMALIZED", "Synthetic jobs normalized.", {"raw_jobs": len(raw_jobs), "unique_jobs": len(canonical_jobs)})

    canonical_db_ids: dict[str, int] = {}
    scored_jobs: list[dict[str, Any]] = []
    approval_queue_summary: list[dict[str, Any]] = []
    applications_awaiting_approval = 0

    for canonical in canonical_jobs:
        canonical_id = _insert_job(connection, run_id, canonical, is_canonical=True)
        canonical_db_ids[canonical.get("external_job_id") or canonical["duplicate_hash"]] = canonical_id

        score = score_job(canonical, settings)
        connection.execute(
            """
            INSERT INTO job_scores
            (run_id, job_id, score_version, fit_score, fit_category, rejected, rejection_reason, factor_scores_json, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                canonical_id,
                score["score_version"],
                score["fit_score"],
                score["fit_category"],
                int(score["rejected"]),
                score["rejection_reason"],
                as_json(score["factor_scores"]),
                score["explanation"],
            ),
        )
        logger.log("JOB_SCORED", "Job scored.", company=canonical["company"], title=canonical["job_title"], score=score["fit_score"], category=score["fit_category"])

        application = prepare_application(canonical, score, settings, root, question_engine)
        resume_label = application["resume"]["label"] if application["resume"] else None
        app_cursor = connection.execute(
            """
            INSERT INTO applications
            (run_id, job_id, resume_used, application_status, application_date, application_method,
             sponsorship_status, notes, strategy_json, submit_allowed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                canonical_id,
                resume_label,
                application["application_status"],
                None,
                "DRY_RUN_SYNTHETIC",
                "UNKNOWN",
                "No real application submitted.",
                as_json(application["strategy"]),
                0,
            ),
        )
        application_id = int(app_cursor.lastrowid)
        if application["application_status"] == "Awaiting Approval":
            applications_awaiting_approval += 1

        for answer in application["screening_answers"]:
            connection.execute(
                """
                INSERT INTO screening_answers
                (run_id, application_id, job_id, question, support_status, answer_text, safe_response,
                 facts_used_json, evidence_sources_json, approval_required, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    application_id,
                    canonical_id,
                    answer["question"],
                    answer["support_status"],
                    answer["answer_text"],
                    answer["safe_response"],
                    as_json(answer["facts_used"]),
                    as_json(answer["evidence_sources"]),
                    int(answer["approval_required"]),
                    answer["reason"],
                ),
            )

        for item in application["approval_items"]:
            approval_queue_summary.append(
                {
                    "job_id": canonical_id,
                    "application_id": application_id,
                    "item_type": item["item_type"],
                    "priority": item["priority"],
                    "question": item.get("question"),
                    "reason": item["reason"],
                }
            )
            connection.execute(
                """
                INSERT INTO approval_queue
                (run_id, item_type, priority, job_id, application_id, question, reason, status, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item["item_type"],
                    item["priority"],
                    canonical_id,
                    application_id,
                    item.get("question"),
                    item["reason"],
                    "OPEN",
                    datetime.now().isoformat(timespec="seconds"),
                    as_json(item.get("metadata", {})),
                ),
            )

        salary = "Not listed"
        if canonical.get("salary_min") or canonical.get("salary_max"):
            salary = f"{canonical.get('currency') or ''} {canonical.get('salary_min') or ''}-{canonical.get('salary_max') or ''}".strip()

        scored_jobs.append(
            {
                "job_id": canonical_id,
                "company": canonical["company"],
                "job_title": canonical["job_title"],
                "location": canonical.get("location"),
                "country": canonical.get("country"),
                "work_mode": canonical.get("work_mode"),
                "salary": salary,
                "salary_max": canonical.get("salary_max"),
                "fit_score": score["fit_score"],
                "fit_category": score["fit_category"],
                "rejection_reason": score["rejection_reason"],
                "explanation": score["explanation"],
                "salary_exception": score.get("salary_exception", {"applies": False}),
                "resume_label": resume_label,
                "application_status": application["application_status"],
                "duplicate_count": canonical.get("duplicate_count", 0),
            }
        )

    for duplicate in duplicate_records:
        canonical_key = duplicate["canonical"].get("external_job_id") or duplicate["canonical"]["duplicate_hash"]
        canonical_id = canonical_db_ids[canonical_key]
        duplicate_id = _insert_job(connection, run_id, duplicate["duplicate"], is_canonical=False, canonical_job_id=canonical_id)
        connection.execute(
            """
            INSERT INTO job_duplicates
            (run_id, canonical_job_id, duplicate_job_id, duplicate_hash, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, canonical_id, duplicate_id, duplicate["duplicate_hash"], duplicate["reason"]),
        )

    category_counts = dict(Counter(item["fit_category"] for item in scored_jobs))
    summary = {
        "run_id": run_id,
        "run_uuid": run_uuid,
        "database_path": str(root / "05_database" / "job_search.sqlite"),
        "raw_jobs_count": len(raw_jobs),
        "unique_jobs_count": len(canonical_jobs),
        "duplicates_count": len(duplicate_records),
        "category_counts": category_counts,
        "applications_awaiting_approval": applications_awaiting_approval,
        "approval_queue_count": len(approval_queue_summary),
        "scored_jobs": sorted(scored_jobs, key=lambda item: item["fit_score"], reverse=True),
        "approval_queue": approval_queue_summary,
        "missing_sources": truth_store.missing_required_sources(),
    }

    report_path = generate_daily_report(root, run_id, summary)
    summary["report_path"] = str(report_path)
    export_path = root / "09_exports" / f"phase1_summary_{run_id}.json"
    write_json(export_path, summary)
    summary["export_path"] = str(export_path)

    insert_event(connection, run_id, "RUN_COMPLETED", "Phase 1 dry-run completed.", {"summary": summary})
    logger.log("RUN_COMPLETED", "Phase 1 dry-run completed.", report=str(report_path), export=str(export_path))
    connection.commit()
    connection.close()
    return summary
