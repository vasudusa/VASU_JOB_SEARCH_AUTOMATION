from __future__ import annotations

import re
from typing import Any

from .normalizer import normalize_text


SCORE_VERSION = "phase1_configurable_v2"


def _contains_any(text: str, terms: list[str]) -> bool:
    normalized_terms = [normalize_text(term) for term in terms]
    return any(term and term in text for term in normalized_terms)


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if normalize_text(term) in text]


def _reject_reason(job: dict[str, Any], settings: dict[str, Any]) -> str | None:
    title = normalize_text(job.get("job_title", ""))
    text = normalize_text(
        " ".join(
            [
                job.get("job_title", ""),
                job.get("description", ""),
                " ".join(job.get("requirements", [])),
            ]
        )
    )
    reject_rules = settings["reject_rules"]

    if _contains_any(title, reject_rules["junior_title_terms"]):
        return "Rejected because the title is below current target seniority."

    if _contains_any(text, reject_rules["low_fit_role_terms"]):
        return "Rejected because the role is primarily support, functional executive, or PMO support."

    for domain_rule in reject_rules["specialist_domains"]:
        has_domain = _contains_any(text, domain_rule["domain_terms"])
        has_specialist_context = _contains_any(text, domain_rule["specialist_context_terms"])
        if has_domain and has_specialist_context:
            return f"Rejected because the role fundamentally requires specialist {domain_rule['domain']} expertise."

    return None


def _role_alignment(job: dict[str, Any], settings: dict[str, Any]) -> int:
    title = normalize_text(job["job_title"])
    targets = settings["target_roles"]
    if any(normalize_text(role) in title for role in targets["priority_1"]):
        return 25
    if any(normalize_text(role) in title for role in targets["priority_2"]):
        return 22
    if any(normalize_text(role) in title for role in targets["priority_3"]):
        return 17
    if "project manager" in title or "program manager" in title:
        return 14
    if "implementation" in title or "delivery" in title:
        return 12
    return 5


def _technical_project_alignment(job: dict[str, Any], settings: dict[str, Any]) -> tuple[int, list[str]]:
    text = normalize_text(
        " ".join(
            [
                job.get("job_title", ""),
                job.get("description", ""),
                " ".join(job.get("requirements", [])),
            ]
        )
    )
    matches = _matched_terms(text, settings["alignment_keywords"])
    score = min(20, round((len(matches) / 9) * 20))
    return score, matches


def _seniority(job: dict[str, Any]) -> int:
    title = normalize_text(job["job_title"])
    if "junior" in title or "coordinator" in title:
        return 2
    if "senior" in title:
        return 15
    if "delivery manager" in title or "implementation manager" in title:
        return 14
    if "technical program manager" in title:
        return 13
    if re.search(r"\bmanager\b", title):
        return 12
    if "lead" in title:
        return 12
    return 7


def _compensation(job: dict[str, Any], settings: dict[str, Any]) -> int:
    salary_max = job.get("salary_max") or 0
    currency = (job.get("currency") or "").upper()
    country = job.get("country") or ""
    if salary_max <= 0:
        return 8
    india_strategy = (
        settings.get("user_approved_application_config", {})
        .get("compensation_strategy", {})
        .get("india", {})
    )
    india_target = india_strategy.get("target_annual_inr", 1500000)
    if country == "India" and currency == "INR":
        if salary_max >= 3000000:
            return 13
        if salary_max >= india_target:
            return 11
        return 6
    if currency == "USD" and salary_max >= 140000:
        return 15
    if currency == "SGD" and salary_max >= 140000:
        return 15
    if currency == "GBP" and salary_max >= 110000:
        return 14
    if currency == "EUR" and salary_max >= 110000:
        return 14
    if currency == "AED" and salary_max >= 280000:
        return 14
    if currency == "AUD" and salary_max >= 160000:
        return 13
    if country and country.lower() != "india":
        return 12
    return 9


def _strategic_salary_exception(
    job: dict[str, Any],
    settings: dict[str, Any],
    factor_scores: dict[str, int],
    rejected: bool,
) -> dict[str, Any]:
    exception_settings = (
        settings.get("user_approved_application_config", {})
        .get("compensation_strategy", {})
        .get("strategic_salary_exception", {})
    )
    india_strategy = (
        settings.get("user_approved_application_config", {})
        .get("compensation_strategy", {})
        .get("india", {})
    )
    label = exception_settings.get("label", "STRATEGIC SALARY EXCEPTION")
    target = india_strategy.get("target_annual_inr", 1500000)
    salary_max = job.get("salary_max") or 0
    applies = (
        bool(exception_settings.get("enabled", False))
        and not rejected
        and job.get("country") == "India"
        and (job.get("currency") or "").upper() == "INR"
        and salary_max > 0
        and salary_max < target
    )

    factors: list[str] = []
    if applies:
        if factor_scores["company_brand_quality"] >= 8:
            factors.append("strong company/brand quality")
        if factor_scores["technical_project_alignment"] >= 15:
            factors.append("strong technical/project alignment")
        if factor_scores["seniority"] >= 12:
            factors.append("senior or leadership scope")
        if factor_scores["career_progression"] >= 4:
            factors.append("career progression value")
        if factor_scores["location_workstyle_fit"] >= 5:
            factors.append("remote/flexible working arrangement")
        if "enterprise" in normalize_text(job.get("description", "")):
            factors.append("enterprise-scale project exposure")
        if len(factors) < 2:
            applies = False

    return {
        "applies": applies,
        "label": label,
        "target_annual_inr": target,
        "salary_max": salary_max,
        "factors": factors,
        "explanation": (
            f"{label}: below INR 15 LPA target, but worth evaluating because "
            + ", ".join(factors)
            if applies
            else ""
        ),
    }


def _international_exposure(job: dict[str, Any]) -> int:
    country = normalize_text(job.get("country", ""))
    location = normalize_text(job.get("location", ""))
    if "remote worldwide" in country or "remote worldwide" in location:
        return 5
    if country and country != "india":
        return 5
    return 2


def _career_progression(job: dict[str, Any]) -> int:
    title = normalize_text(job["job_title"])
    if any(term in title for term in ["senior", "delivery manager", "technical program manager", "enterprise implementation lead"]):
        return 5
    if "manager" in title or "lead" in title:
        return 4
    return 2


def _location_workstyle(job: dict[str, Any], settings: dict[str, Any]) -> int:
    country = job.get("country") or ""
    work_mode = normalize_text(job.get("work_mode", ""))
    score = 0
    if country in settings["target_countries"]:
        score += 3
    if any(mode in work_mode for mode in ["remote", "hybrid"]):
        score += 2
    elif "on site" in work_mode or "onsite" in work_mode:
        score += 1
    return min(score, 5)


def category_for_score(score: int, rejected: bool, settings: dict[str, Any]) -> str:
    if rejected or score < settings["thresholds"]["stretch"]:
        return "REJECT"
    if score >= settings["thresholds"]["strong"]:
        return "STRONG"
    if score >= settings["thresholds"]["good"]:
        return "GOOD"
    return "STRETCH"


def score_job(job: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    rejection = _reject_reason(job, settings)

    factor_scores: dict[str, int] = {
        "role_alignment": _role_alignment(job, settings),
        "technical_project_alignment": 0,
        "seniority": _seniority(job),
        "compensation_potential": _compensation(job, settings),
        "company_brand_quality": int(job.get("company_brand_score", 5)),
        "international_exposure": _international_exposure(job),
        "career_progression": _career_progression(job),
        "location_workstyle_fit": _location_workstyle(job, settings),
    }
    technical_score, matches = _technical_project_alignment(job, settings)
    factor_scores["technical_project_alignment"] = technical_score

    if rejection:
        total = min(45, max(20, factor_scores["role_alignment"] + technical_score))
        rejected = True
    else:
        total = sum(factor_scores.values())
        rejected = total < settings["thresholds"]["stretch"]

    category = category_for_score(total, rejected, settings)
    salary_exception = _strategic_salary_exception(job, settings, factor_scores, rejected)
    explanation_parts = [
        f"Role alignment {factor_scores['role_alignment']}/25",
        f"technical/project alignment {factor_scores['technical_project_alignment']}/20",
        f"seniority {factor_scores['seniority']}/15",
        f"compensation {factor_scores['compensation_potential']}/15",
        f"brand {factor_scores['company_brand_quality']}/10",
        f"international exposure {factor_scores['international_exposure']}/5",
        f"career progression {factor_scores['career_progression']}/5",
        f"location/workstyle {factor_scores['location_workstyle_fit']}/5",
    ]
    if matches:
        explanation_parts.append("matched: " + ", ".join(matches[:8]))
    if salary_exception["applies"]:
        explanation_parts.append(salary_exception["explanation"])
    if rejection:
        explanation_parts.append(rejection)

    return {
        "score_version": SCORE_VERSION,
        "fit_score": int(total),
        "fit_category": category,
        "rejected": rejected,
        "rejection_reason": rejection,
        "factor_scores": factor_scores,
        "matched_terms": matches,
        "salary_exception": salary_exception,
        "explanation": "; ".join(explanation_parts),
    }
