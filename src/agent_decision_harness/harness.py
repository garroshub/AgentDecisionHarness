from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .applicability import (
    ApplicabilityResult,
    DeploymentContext,
    ValidatedScope,
    check_applicability,
)
from .audit import AuditResult, audit_record
from .finalization import FrozenFinalizer
from .policy_spec import DEFAULT_POLICY, PolicySpec
from .qualification import QualificationEvidence
from .records import ForecastRecord
from .routing import (
    DisagreementState,
    classify_disagreement,
    majority_record,
    routing_trigger,
)
from .task_spec import DEFAULT_TASK, TaskSpec


@dataclass(frozen=True)
class DecisionResult:
    action: str
    authority: str
    baseline_record: ForecastRecord
    final_record: ForecastRecord
    disagreement: DisagreementState
    qualification: QualificationEvidence
    applicability: ApplicabilityResult
    audit: AuditResult
    task: TaskSpec
    policy: PolicySpec
    configuration_fingerprint: str | None
    trace: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "authority": self.authority,
            "configuration_fingerprint": self.configuration_fingerprint,
            "task": self.task.to_dict(),
            "policy": self.policy.to_dict(),
            "disagreement": {
                "state": self.disagreement.state,
                "vote_labels": list(self.disagreement.vote_labels),
                "majority_label": self.disagreement.majority_label,
                "majority_count": self.disagreement.majority_count,
                "total_count": self.disagreement.total_count,
                "auxiliary_label": self.disagreement.auxiliary_label,
                "auxiliary_relation": self.disagreement.auxiliary_relation,
                "conflict": self.disagreement.conflict,
            },
            "qualification": {
                "specialist_id": self.qualification.specialist_id,
                "status": self.qualification.status,
                "evidence_source": self.qualification.evidence_source,
                "evaluated_task": self.qualification.evaluated_task,
                "control": self.qualification.control,
                "note": self.qualification.note,
                "provider": self.qualification.provider,
                "backbone": self.qualification.backbone,
                "configuration_fingerprint": (
                    self.qualification.configuration_fingerprint
                ),
            },
            "applicability": {
                "passed": self.applicability.passed,
                "checks": self.applicability.checks,
                "reasons": list(self.applicability.reasons),
            },
            "baseline_record": self.baseline_record.to_dict(
                self.task.interval_level
            ),
            "final_record": self.final_record.to_dict(
                self.task.interval_level
            ),
            "audit": {
                "passed": self.audit.passed,
                "checks": self.audit.checks,
            },
            "trace": list(self.trace),
        }


class AgentDecisionHarness:
    def decide(
        self,
        *,
        candidates: list[ForecastRecord],
        auxiliary_label: str,
        qualification: QualificationEvidence,
        validated_scope: ValidatedScope,
        deployment: DeploymentContext,
        evidence_text: str,
        finalizer: FrozenFinalizer | None = None,
        task: TaskSpec = DEFAULT_TASK,
        policy: PolicySpec = DEFAULT_POLICY,
        configuration_fingerprint: str | None = None,
    ) -> DecisionResult:
        task.validate()
        policy.validate()
        if len(candidates) != policy.draws:
            raise ValueError(
                f"policy requires {policy.draws} candidate records; "
                f"received {len(candidates)}"
            )

        valid_candidates = [
            record
            for record in candidates
            if record.is_valid(evidence_text, task)
        ]
        if len(valid_candidates) != len(candidates):
            raise ValueError(
                "one or more candidate records failed validation"
            )

        applicability = check_applicability(validated_scope, deployment)
        disagreement = classify_disagreement(
            valid_candidates,
            auxiliary_label,
        )
        baseline = majority_record(
            valid_candidates,
            disagreement.majority_label,
        )

        qualification_match = (
            qualification.allows_authority
            and qualification.matches_configuration(
                configuration_fingerprint
            )
        )
        qualification_ok = (
            qualification_match
            or not policy.qualification_required
        )
        applicability_ok = (
            applicability.passed
            or not policy.applicability_required
        )
        trigger = routing_trigger(disagreement, policy)
        should_route = trigger and qualification_ok and applicability_ok

        trace = [
            f"candidate_validation=PASS ({len(valid_candidates)}/{len(candidates)})",
            f"task={task.task_id}",
            f"policy={policy.policy_id}",
            f"qualification={qualification.status.upper()}",
            "configuration_match="
            + ("PASS" if qualification.matches_configuration(
                configuration_fingerprint
            ) else "FAIL"),
            "applicability="
            + ("PASS" if applicability.passed else "FAIL"),
            f"disagreement_state={disagreement.state}",
        ]

        if should_route:
            if finalizer is None:
                raise ValueError(
                    "routing triggered but no finalizer was provided"
                )
            final_record = finalizer.finalize(auxiliary_label)
            if not final_record.is_valid(evidence_text, task):
                raise ValueError("finalized record failed validation")
            action = "route_and_finalize_complete_record"
            authority = qualification.specialist_id
            trace.append(f"forecast_authority={authority}")
            trace.append("complete_record_finalization=TRIGGERED")
        else:
            final_record = baseline
            action = "retain_majority_record"
            authority = "llm_majority"
            if trigger and not qualification_ok:
                trace.append("routing_blocked=QUALIFICATION")
            elif trigger and not applicability_ok:
                trace.append("routing_blocked=APPLICABILITY")
            else:
                trace.append("routing_trigger=INACTIVE")
            trace.append("forecast_authority=llm_majority")

        audit = audit_record(final_record, evidence_text, task)
        trace.append(
            "final_record_audit="
            + ("PASS" if audit.passed else "FAIL")
        )

        return DecisionResult(
            action=action,
            authority=authority,
            baseline_record=baseline,
            final_record=final_record,
            disagreement=disagreement,
            qualification=qualification,
            applicability=applicability,
            audit=audit,
            task=task,
            policy=policy,
            configuration_fingerprint=configuration_fingerprint,
            trace=tuple(trace),
        )
