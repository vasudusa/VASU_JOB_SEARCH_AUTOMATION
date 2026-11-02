from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from jobsearch.application_engine import prepare_application
from jobsearch.config import load_settings, load_synthetic_jobs, load_truth_store
from jobsearch.deduplication import deduplicate_jobs
from jobsearch.normalizer import normalize_jobs
from jobsearch.pipeline import run_phase1
from jobsearch.question_engine import QuestionEngine
from jobsearch.scoring import score_job
from jobsearch.truth_store import TruthStore


class Phase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = load_settings(ROOT)
        cls.truth_store = TruthStore(load_truth_store(ROOT))
        cls.question_engine = QuestionEngine(cls.truth_store)
        cls.jobs = normalize_jobs(load_synthetic_jobs(ROOT))

    def job_by_external_id(self, external_id: str) -> dict:
        for job in self.jobs:
            if job["external_job_id"] == external_id:
                return job
        raise AssertionError(f"Missing synthetic job {external_id}")

    def test_good_tpm_job_scores_strong(self) -> None:
        job = self.job_by_external_id("NIM-TPM-001")
        score = score_job(job, self.settings)
        self.assertEqual(score["fit_category"], "STRONG")
        self.assertGreaterEqual(score["fit_score"], 85)

    def test_specialist_sap_job_is_rejected(self) -> None:
        job = self.job_by_external_id("ERP-SAP-222")
        score = score_job(job, self.settings)
        self.assertEqual(score["fit_category"], "REJECT")
        self.assertIn("SAP", score["rejection_reason"])

    def test_junior_role_is_rejected(self) -> None:
        job = self.job_by_external_id("LOCAL-JPC-010")
        score = score_job(job, self.settings)
        self.assertEqual(score["fit_category"], "REJECT")
        self.assertIn("below current target seniority", score["rejection_reason"])

    def test_hrms_senior_pm_role_can_score_highly(self) -> None:
        job = self.job_by_external_id("PCL-HRMS-909")
        score = score_job(job, self.settings)
        self.assertIn(score["fit_category"], {"STRONG", "GOOD"})
        self.assertGreaterEqual(score["fit_score"], 70)

    def test_deduplication_prefers_company_careers(self) -> None:
        canonical, duplicates = deduplicate_jobs(self.jobs)
        nimbus = [job for job in canonical if job["company"] == "Nimbus HR Tech"]
        self.assertEqual(len(nimbus), 1)
        self.assertEqual(nimbus[0]["source"], "company_careers")
        self.assertEqual(len([dup for dup in duplicates if dup["canonical"]["company"] == "Nimbus HR Tech"]), 1)

    def test_unsupported_questions_trigger_human_review(self) -> None:
        answer = self.question_engine.answer("Are you PMP certified?")
        self.assertEqual(answer["support_status"], "UNSUPPORTED")
        self.assertFalse(answer["can_answer"])
        self.assertTrue(answer["approval_required"])

    def test_missing_notice_period_is_not_invented(self) -> None:
        answer = self.question_engine.answer("What is your notice period?")
        self.assertEqual(answer["support_status"], "UNKNOWN")
        self.assertIsNone(answer["answer_text"])
        self.assertTrue(answer["approval_required"])

    def test_nsci_go_live_is_never_claimed_completed(self) -> None:
        answer = self.question_engine.answer("Has the NSCI project gone live?")
        self.assertEqual(answer["support_status"], "UNSUPPORTED")
        self.assertIn("Do not claim NSCI Go-Live was completed", answer["safe_response"])

    def test_sap_functional_expertise_is_not_claimed(self) -> None:
        answer = self.question_engine.answer("Describe your SAP functional expertise.")
        self.assertEqual(answer["support_status"], "UNSUPPORTED")
        self.assertFalse(answer["can_answer"])
        self.assertIn("SAP functional expertise", answer["safe_response"])

    def test_technical_coordination_and_ownership_are_distinguished(self) -> None:
        answer = self.question_engine.answer("Describe your technical integration ownership.")
        self.assertEqual(answer["support_status"], "PARTIAL")
        self.assertTrue(answer["approval_required"])
        self.assertIn("coordination", answer["safe_response"].lower())

    def test_captcha_flag_triggers_pause(self) -> None:
        job = self.job_by_external_id("CLOUD-TPGM-515")
        score = score_job(job, self.settings)
        package = prepare_application(job, score, self.settings, ROOT, self.question_engine)
        reasons = " ".join(item["reason"] for item in package["approval_items"])
        self.assertIn("captcha", reasons.lower())

    def test_phase1_pipeline_runs_end_to_end(self) -> None:
        summary = run_phase1(ROOT, reset_db=True)
        self.assertEqual(summary["raw_jobs_count"], 9)
        self.assertEqual(summary["unique_jobs_count"], 8)
        self.assertEqual(summary["duplicates_count"], 1)
        self.assertGreater(summary["approval_queue_count"], 0)
        self.assertTrue(Path(summary["database_path"]).exists())
        self.assertTrue(Path(summary["report_path"]).exists())


if __name__ == "__main__":
    unittest.main()

