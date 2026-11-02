from __future__ import annotations

from typing import Any

from .normalizer import normalize_text
from .truth_store import TruthStore


def _result(
    question: str,
    support_status: str,
    can_answer: bool,
    answer_text: str | None,
    safe_response: str,
    facts_used: list[str],
    truth_store: TruthStore,
    reason: str,
    approval_required: bool,
    evidence_sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "question": question,
        "support_status": support_status,
        "can_answer": can_answer,
        "answer_text": answer_text if can_answer else None,
        "safe_response": safe_response,
        "facts_used": facts_used,
        "evidence_sources": evidence_sources if evidence_sources is not None else truth_store.evidence_sources_for(facts_used),
        "approval_required": approval_required,
        "reason": reason,
    }


class QuestionEngine:
    def __init__(self, truth_store: TruthStore, settings: dict[str, Any] | None = None) -> None:
        self.truth_store = truth_store
        self.settings = settings or {}

    def _approved_config(self) -> dict[str, Any]:
        return self.settings.get("user_approved_application_config", {})

    def _config_source_id(self) -> str:
        return self._approved_config().get("source_id", "user_approved_configuration")

    def answer(self, question: str, job: dict[str, Any] | None = None) -> dict[str, Any]:
        q = normalize_text(question)
        approved_config = self._approved_config()
        personal_config = approved_config.get("personal", {})
        compensation_config = approved_config.get("compensation_strategy", {})
        authorization_config = approved_config.get("work_authorization", {})
        claim_rules = approved_config.get("professional_claim_rules", {})
        config_source = self._config_source_id()

        if "notice" in q:
            notice_period = personal_config.get("notice_period_label")
            if notice_period:
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    f"My notice period is {notice_period}.",
                    f"My notice period is {notice_period}.",
                    ["config.personal.notice_period"],
                    self.truth_store,
                    "Notice period is from explicit user-approved configuration.",
                    False,
                    [config_source],
                )
            fact_id = "profile.notice_period"
            return _result(
                question,
                "UNKNOWN",
                False,
                None,
                "Notice period is not configured. Pause for Vasu confirmation.",
                [fact_id],
                self.truth_store,
                "Notice period must not be guessed.",
                True,
            )

        if "salary" in q or "compensation" in q or "ctc" in q:
            job_country = (job or {}).get("country")
            india_strategy = compensation_config.get("india", {})
            international_strategy = compensation_config.get("international", {})
            if job_country == "India" and india_strategy.get("target_label"):
                answer = (
                    f"My India target compensation is {india_strategy['target_label']}. "
                    "This is not a hard rejection threshold; strategic roles may still be worth evaluating."
                )
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    answer,
                    answer,
                    ["config.compensation_strategy.india"],
                    self.truth_store,
                    "India compensation strategy is from explicit user-approved configuration.",
                    True,
                    [config_source],
                )
            if international_strategy:
                answer = (
                    "For international roles, compensation should be evaluated against local market, seniority, "
                    "company quality, relocation value, sponsorship, cost-of-living context where available, "
                    "international career value, and future progression."
                )
                return _result(
                    question,
                    "PARTIAL",
                    True,
                    answer,
                    answer,
                    ["config.compensation_strategy.international"],
                    self.truth_store,
                    "International salary expectation requires role/country-specific review.",
                    True,
                    [config_source],
                )
            fact_id = "profile.salary_expectations"
            return _result(
                question,
                "UNKNOWN",
                False,
                None,
                "Salary expectation is not configured. Pause for role/country/currency-specific input.",
                [fact_id],
                self.truth_store,
                "Salary expectations must not be invented.",
                True,
            )

        if "authorization" in q or "work permit" in q or "visa" in q or "sponsorship" in q:
            job_country = (job or {}).get("country")
            if authorization_config:
                if job_country == "India":
                    answer = f"I am {authorization_config['india']} for India."
                    return _result(
                        question,
                        "SUPPORTED",
                        True,
                        answer,
                        answer,
                        ["config.work_authorization.india"],
                        self.truth_store,
                        "India work authorization is from explicit user-approved configuration.",
                        False,
                        [config_source],
                    )
                answer = (
                    f"My foreign work authorization status is: {authorization_config['foreign']}. "
                    f"{authorization_config['sponsorship_required_opportunities']}"
                )
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    answer,
                    answer,
                    ["config.work_authorization.foreign"],
                    self.truth_store,
                    "Foreign authorization and sponsorship preference are from explicit user-approved configuration.",
                    True,
                    [config_source],
                )
            fact_id = "profile.work_authorization"
            return _result(
                question,
                "UNKNOWN",
                False,
                None,
                "Work authorization and sponsorship status are not configured. Pause for confirmation.",
                [fact_id],
                self.truth_store,
                "Work authorization must not be invented.",
                True,
            )

        if "pmp" in q:
            if claim_rules.get("pmp"):
                answer = "I am not PMP certified yet."
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    answer,
                    answer,
                    ["config.professional_claim_rules.pmp"],
                    self.truth_store,
                    "PMP status is from explicit user-approved configuration.",
                    False,
                    [config_source],
                )
            fact_id = "credential.pmp"
            return _result(
                question,
                "UNSUPPORTED",
                False,
                None,
                "Do not claim PMP certification unless Vasu provides approved evidence.",
                [fact_id],
                self.truth_store,
                "No approved evidence confirms PMP certification.",
                True,
            )

        if "certified" in q or "certification" in q:
            fact_id = "credential.certifications"
            return _result(
                question,
                "UNKNOWN",
                False,
                None,
                "Certification details are not fully verified. Pause for approved resume or certificate evidence.",
                [fact_id],
                self.truth_store,
                "Certifications must not be invented.",
                True,
            )

        if "sap" in q:
            if any(term in q for term in ["functional", "expert", "consultant", "module", "certified"]):
                if claim_rules.get("sap_functional_expertise") is False:
                    answer = "No. I should not be represented as having SAP functional expertise."
                    return _result(
                        question,
                        "SUPPORTED",
                        True,
                        answer,
                        answer,
                        ["config.professional_claim_rules.sap_functional_expertise"],
                        self.truth_store,
                        "SAP functional expertise is explicitly denied in user-approved configuration.",
                        False,
                        [config_source],
                    )
                fact_id = "capability.sap_functional_expertise"
                return _result(
                    question,
                    "UNSUPPORTED",
                    False,
                    None,
                    "Do not claim SAP functional expertise. Approved facts support SAP-related requirements or coordination only.",
                    [fact_id, "capability.sap_related_coordination"],
                    self.truth_store,
                    "SAP functional expertise is explicitly unsupported.",
                    True,
                )
            fact_id = "capability.sap_related_coordination"
            return _result(
                question,
                "PARTIAL",
                True,
                self.truth_store.get(fact_id)["allowed_statement"],
                self.truth_store.get(fact_id)["allowed_statement"],
                [fact_id],
                self.truth_store,
                "SAP-related coordination is supported but must not be overstated.",
                True,
            )

        if "nsci" in q and ("live" in q or "go live" in q or "go" in q):
            if claim_rules.get("nsci_go_live_completed") is False:
                answer = "No. Do not claim NSCI Go-Live completion; latest approved status says Go-Live was pending."
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    answer,
                    answer,
                    ["config.professional_claim_rules.nsci_go_live_completed", "project.nsci_status"],
                    self.truth_store,
                    "NSCI Go-Live completion is explicitly disallowed in user-approved configuration.",
                    False,
                    [config_source],
                )
            fact_id = "project.nsci_go_live_completed"
            return _result(
                question,
                "UNSUPPORTED",
                False,
                None,
                "Do not claim NSCI Go-Live was completed. Latest approved status says Go-Live was pending.",
                [fact_id, "project.nsci_status"],
                self.truth_store,
                "NSCI Go-Live completion is explicitly unsupported.",
                True,
            )

        if "people management" in q or "direct report" in q or "team size" in q or "managed people" in q:
            if claim_rules.get("direct_people_management"):
                answer = "No formal direct-report people-management experience should currently be claimed."
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    answer,
                    answer,
                    ["config.professional_claim_rules.direct_people_management"],
                    self.truth_store,
                    "Direct people-management claim rule is from explicit user-approved configuration.",
                    False,
                    [config_source],
                )
            fact_id = "profile.people_management"
            return _result(
                question,
                "UNKNOWN",
                False,
                None,
                "Direct people-management experience is not verified. Pause for Vasu confirmation.",
                [fact_id],
                self.truth_store,
                "People-management experience must not be invented.",
                True,
            )

        if "technical integration ownership" in q or "owned integration" in q or "ownership" in q:
            if claim_rules.get("technical_leadership") and claim_rules.get("project_team_coordination"):
                answer = (
                    "Technical leadership and project/team coordination are supported. "
                    "For integrations, describe technical coordination and leadership without claiming unsupported sole ownership."
                )
                return _result(
                    question,
                    "PARTIAL",
                    True,
                    answer,
                    answer,
                    ["config.professional_claim_rules.technical_leadership", "capability.technical_coordination_vs_ownership"],
                    self.truth_store,
                    "Technical leadership is configured, while sole integration ownership remains bounded by approved evidence.",
                    True,
                    [config_source],
                )
            fact_id = "capability.technical_coordination_vs_ownership"
            return _result(
                question,
                "PARTIAL",
                True,
                self.truth_store.get(fact_id)["allowed_statement"],
                self.truth_store.get(fact_id)["allowed_statement"],
                [fact_id, "profile.pm_responsibilities"],
                self.truth_store,
                "Coordination is supported; sole ownership is not verified.",
                True,
            )

        if "current location" in q or q == "location" or "where are you based" in q:
            if personal_config.get("current_location"):
                answer = f"I am based in {personal_config['current_location']}."
                return _result(
                    question,
                    "SUPPORTED",
                    True,
                    answer,
                    answer,
                    ["config.personal.current_location"],
                    self.truth_store,
                    "Current location is from explicit user-approved configuration.",
                    False,
                    [config_source],
                )
            fact_id = "profile.location"
            return _result(
                question,
                "SUPPORTED",
                True,
                self.truth_store.get(fact_id)["allowed_statement"],
                self.truth_store.get(fact_id)["allowed_statement"],
                [fact_id],
                self.truth_store,
                "Location is supported by the approved profile.",
                False,
            )

        if "relocat" in q:
            fact_id = "preference.relocation"
            return _result(
                question,
                "SUPPORTED",
                True,
                self.truth_store.get(fact_id)["allowed_statement"],
                self.truth_store.get(fact_id)["allowed_statement"],
                [fact_id],
                self.truth_store,
                "Relocation and work-style preferences are supported.",
                False,
            )

        if "years" in q and "experience" in q:
            fact_id = "profile.it_experience"
            return _result(
                question,
                "SUPPORTED",
                True,
                self.truth_store.get(fact_id)["allowed_statement"],
                self.truth_store.get(fact_id)["allowed_statement"],
                [fact_id],
                self.truth_store,
                "Approximate IT experience is supported by the approved profile.",
                False,
            )

        if any(term in q for term in ["stakeholder", "governance", "implementation", "integration", "api", "sql"]):
            fact_id = "profile.pm_responsibilities"
            return _result(
                question,
                "SUPPORTED",
                True,
                self.truth_store.get(fact_id)["allowed_statement"],
                self.truth_store.get(fact_id)["allowed_statement"],
                [fact_id],
                self.truth_store,
                "PM responsibilities are supported by the approved profile.",
                False,
            )

        return _result(
            question,
            "UNKNOWN",
            False,
            None,
            "No approved fact matched this question. Pause for human review.",
            [],
            self.truth_store,
            "The system cannot infer missing facts.",
            True,
        )
