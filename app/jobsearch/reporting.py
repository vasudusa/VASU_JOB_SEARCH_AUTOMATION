from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_daily_report(root: Path, run_id: str, summary: dict[str, Any]) -> Path:
    report_path = root / "06_reports" / f"daily_report_{run_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Daily Job Search Dry-Run Report - {run_id}")
    lines.append("")
    lines.append("Mode: DRY_RUN. No real applications were submitted.")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- New jobs found: {summary['raw_jobs_count']}")
    lines.append(f"- Unique jobs after dedupe: {summary['unique_jobs_count']}")
    lines.append(f"- Duplicate listings removed: {summary['duplicates_count']}")
    lines.append(f"- Strong matches: {summary['category_counts'].get('STRONG', 0)}")
    lines.append(f"- Good matches: {summary['category_counts'].get('GOOD', 0)}")
    lines.append(f"- Stretch matches: {summary['category_counts'].get('STRETCH', 0)}")
    lines.append(f"- Rejected jobs: {summary['category_counts'].get('REJECT', 0)}")
    lines.append(f"- Applications submitted: 0")
    lines.append(f"- Applications awaiting approval: {summary['applications_awaiting_approval']}")
    lines.append(f"- Approval queue items: {summary['approval_queue_count']}")
    lines.append("")

    lines.append("## Strong And Good Matches")
    for item in summary["scored_jobs"]:
        if item["fit_category"] in {"STRONG", "GOOD"}:
            lines.append("")
            lines.append(f"### {item['company']} - {item['job_title']}")
            lines.append(f"- Location: {item['location']} ({item['country']})")
            lines.append(f"- Work mode: {item['work_mode']}")
            lines.append(f"- Salary: {item['salary']}")
            lines.append(f"- Score: {item['fit_score']} ({item['fit_category']})")
            lines.append(f"- Resume: {item['resume_label']}")
            lines.append(f"- Application status: {item['application_status']}")
            salary_exception = item.get("salary_exception") or {}
            if salary_exception.get("applies"):
                lines.append(f"- Salary note: {salary_exception['label']} - {salary_exception['explanation']}")
            lines.append(f"- Why: {item['explanation']}")

    lines.append("")
    lines.append("## Strategic Salary Exceptions")
    salary_exceptions = [
        item for item in summary["scored_jobs"]
        if (item.get("salary_exception") or {}).get("applies")
    ]
    if salary_exceptions:
        for item in salary_exceptions:
            exception = item["salary_exception"]
            lines.append(f"- {item['company']} - {item['job_title']}: {exception['explanation']}")
    else:
        lines.append("- None in this dry-run.")

    lines.append("")
    lines.append("## International Opportunities")
    for item in summary["scored_jobs"]:
        if item["country"] and item["country"] != "India" and item["fit_category"] != "REJECT":
            lines.append(f"- {item['company']} - {item['job_title']} - {item['country']} - {item['fit_score']}")

    lines.append("")
    lines.append("## Sponsorship / Authorization Items")
    sponsorship_items = [
        item for item in summary["approval_queue"]
        if "authorization" in item["reason"].lower() or "sponsorship" in item["reason"].lower()
    ]
    if sponsorship_items:
        for item in sponsorship_items:
            lines.append(f"- Job ID {item.get('job_id')}: {item['reason']}")
    else:
        lines.append("- None found.")

    lines.append("")
    lines.append("## Highest Paying Opportunities")
    for item in sorted(summary["scored_jobs"], key=lambda value: value["salary_max"] or 0, reverse=True)[:5]:
        lines.append(f"- {item['company']} - {item['job_title']} - {item['salary']} - {item['fit_category']}")

    lines.append("")
    lines.append("## Rejected Jobs")
    for item in summary["scored_jobs"]:
        if item["fit_category"] == "REJECT":
            lines.append(f"- {item['company']} - {item['job_title']} - {item['rejection_reason']}")

    lines.append("")
    lines.append("## Important Deadlines")
    lines.append("- No real application deadlines were collected in Phase 1 synthetic data.")

    lines.append("")
    lines.append("## Required Human Input")
    for item in summary["approval_queue"][:30]:
        lines.append(f"- {item['item_type']} ({item['priority']}): {item['reason']}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path
