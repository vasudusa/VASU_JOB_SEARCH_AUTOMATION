from __future__ import annotations

from pathlib import Path
from typing import Any

from .question_engine import QuestionEngine


def select_resume(job: dict[str, Any], settings: dict[str, Any], root: Path) -> dict[str, Any]:
    title = job["normalized_title"]
    country = job.get("country") or ""
    variants = settings["resume_variants"]

    if "technical program manager" in title or "program manager" in title:
        key = "product_program"
    elif country and country != "India":
        key = "international_implementation"
    elif "senior technical project manager" in title:
        key = "master_senior_tpm"
    elif "technical project manager" in title:
        key = "technical_project_manager"
    elif "implementation" in title or "delivery" in title:
        key = "international_implementation" if country != "India" else "technical_project_manager"
    else:
        key = "master_senior_tpm"

    variant = dict(variants[key])
    variant["key"] = key
    variant["absolute_path"] = str((root / variant["path"]).resolve())
    variant["exists_on_disk"] = (root / variant["path"]).exists()
    return variant


def prepare_application(
    job: dict[str, Any],
    score: dict[str, Any],
    settings: dict[str, Any],
    root: Path,
    question_engine: QuestionEngine,
) -> dict[str, Any]:
    if score["fit_category"] == "REJECT":
        return {
            "application_status": "Rejected",
            "resume": None,
            "strategy": {
                "mode": "DRY_RUN",
                "submit_allowed": False,
                "reason": score["rejection_reason"] or "Score below threshold.",
            },
            "screening_answers": [],
            "approval_items": [],
        }

    resume = select_resume(job, settings, root)
    questions = list(settings.get("screening_questions", []))
    for question in job.get("screening_questions", []):
        if question not in questions:
            questions.append(question)

    answers = [question_engine.answer(question, job=job) for question in questions]
    approval_items: list[dict[str, Any]] = []

    if not resume["exists_on_disk"]:
        approval_items.append(
            {
                "item_type": "MISSING_RESUME",
                "priority": "HIGH",
                "question": None,
                "reason": f"Resume file is missing: {resume['path']}",
                "metadata": resume,
            }
        )

    for answer in answers:
        if answer["approval_required"] or not answer["can_answer"]:
            approval_items.append(
                {
                    "item_type": "SCREENING_QUESTION_REVIEW",
                    "priority": "HIGH" if answer["support_status"] in {"UNKNOWN", "UNSUPPORTED"} else "MEDIUM",
                    "question": answer["question"],
                    "reason": answer["reason"],
                    "metadata": answer,
                }
            )

    for flag in job.get("simulated_site_flags", []):
        if flag.lower() in {"captcha", "mfa", "authentication_challenge"}:
            approval_items.append(
                {
                    "item_type": "HUMAN_INTERVENTION_REQUIRED",
                    "priority": "HIGH",
                    "question": None,
                    "reason": f"Simulated application site flag requires pause: {flag}",
                    "metadata": {"site_flag": flag},
                }
            )

    if score["fit_score"] >= settings["thresholds"]["human_approval_threshold"]:
        status = "Awaiting Approval"
        approval_items.append(
            {
                "item_type": "APPLICATION_APPROVAL",
                "priority": "MEDIUM",
                "question": None,
                "reason": "Dry-run application package prepared; human approval required before any real submission.",
                "metadata": {"fit_score": score["fit_score"], "fit_category": score["fit_category"]},
            }
        )
    else:
        status = "Prepared"

    strategy = {
        "mode": "DRY_RUN",
        "submit_allowed": False,
        "fit_category": score["fit_category"],
        "fit_score": score["fit_score"],
        "resume_variant": resume["key"],
        "resume_label": resume["label"],
        "resume_exists_on_disk": resume["exists_on_disk"],
        "matched_terms": score.get("matched_terms", []),
        "salary_exception": score.get("salary_exception", {"applies": False}),
        "risk_flags": [
            item["reason"]
            for item in approval_items
            if item["priority"] == "HIGH"
        ],
    }

    return {
        "application_status": status,
        "resume": resume,
        "strategy": strategy,
        "screening_answers": answers,
        "approval_items": approval_items,
    }
