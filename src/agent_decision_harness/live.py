from __future__ import annotations

import re
from typing import Any, Mapping, Protocol

from .applicability import (
    DeploymentContext,
    ValidatedScope,
)
from .configuration import (
    case_configuration_fingerprint,
    resolve_specs,
)
from .finalization import FrozenFinalizer
from .harness import (
    AgentDecisionHarness,
    DecisionResult,
)
from .policy_spec import PolicySpec
from .qualification import QualificationEvidence
from .records import ForecastRecord
from .task_spec import TaskSpec

SUPPORTED_LIVE_PROVIDERS = frozenset(
    {"codex", "claude"}
)

_BLOCKED_RUNTIME_KEYS = {
    "actual_label",
    "actual_return",
    "ground_truth",
    "oracle",
    "oracle_value",
    "realized_label",
    "realized_outcome",
    "realized_return",
    "observed_return",
}


class CandidateProvider(Protocol):
    provider_name: str
    model: str

    def generate(
        self,
        case_view: Mapping[str, Any],
        draw_index: int,
        task: TaskSpec,
        draws: int,
    ) -> ForecastRecord: ...


def _canonical_key(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).lower(),
    ).strip("_")


def assert_no_realized_outcome(
    value: Any,
    path: str = "case",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = _canonical_key(key)
            if normalized in _BLOCKED_RUNTIME_KEYS:
                raise ValueError(
                    "live case contains forbidden field "
                    f"{path}.{key}"
                )
            assert_no_realized_outcome(
                child,
                f"{path}.{key}",
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_realized_outcome(
                child,
                f"{path}[{index}]",
            )


def _require_nonempty(
    mapping: dict[str, Any],
    key: str,
    label: str,
) -> str:
    value = str(mapping.get(key, "")).strip()
    if not value:
        raise ValueError(
            f"{label}.{key} must be non-empty"
        )
    return value


def validate_live_case(
    d: dict[str, Any],
    *,
    task_override: dict[str, Any] | None = None,
    policy_override: dict[str, Any] | None = None,
) -> tuple[TaskSpec, PolicySpec, str]:
    assert_no_realized_outcome(d)

    required = {
        "case_id",
        "evidence_text",
        "deployment_context",
        "validated_scope",
        "qualification",
        "auxiliary",
    }
    missing = sorted(required - set(d))
    if missing:
        raise ValueError(
            f"live case is missing fields: {missing}"
        )
    if "candidates" in d:
        raise ValueError(
            "live case must not contain candidates"
        )
    if "expected" in d:
        raise ValueError(
            "live case must not contain replay expectations"
        )
    if not str(d["evidence_text"]).strip():
        raise ValueError(
            "live case evidence_text must be non-empty"
        )

    deployment = d["deployment_context"]
    scope = d["validated_scope"]
    qualification = d["qualification"]
    if not all(
        isinstance(item, dict)
        for item in (
            deployment,
            scope,
            qualification,
        )
    ):
        raise ValueError(
            "deployment, scope, and qualification "
            "must be objects"
        )

    provider = _require_nonempty(
        deployment,
        "provider",
        "deployment_context",
    ).lower()
    if provider not in SUPPORTED_LIVE_PROVIDERS:
        raise ValueError(
            f"unsupported provider {provider!r}"
        )
    backbone = _require_nonempty(
        deployment,
        "backbone",
        "deployment_context",
    )
    scope_provider = _require_nonempty(
        scope,
        "provider",
        "validated_scope",
    ).lower()
    scope_backbone = _require_nonempty(
        scope,
        "backbone",
        "validated_scope",
    )
    qualification_provider = _require_nonempty(
        qualification,
        "provider",
        "qualification",
    ).lower()
    qualification_backbone = _require_nonempty(
        qualification,
        "backbone",
        "qualification",
    )

    if scope_provider != provider:
        raise ValueError(
            "validated_scope.provider mismatch"
        )
    if scope_backbone != backbone:
        raise ValueError(
            "validated_scope.backbone mismatch"
        )
    if qualification_provider != provider:
        raise ValueError(
            "qualification.provider mismatch"
        )
    if qualification_backbone != backbone:
        raise ValueError(
            "qualification.backbone mismatch"
        )

    task, policy = resolve_specs(
        d,
        task_override=task_override,
        policy_override=policy_override,
    )
    fingerprint = case_configuration_fingerprint(
        d,
        task,
        policy,
    )

    auxiliary = d["auxiliary"]
    if not isinstance(auxiliary, dict):
        raise ValueError("auxiliary must be an object")
    if set(auxiliary) != {
        "label",
        "complete_record",
    }:
        raise ValueError(
            "auxiliary must contain label and complete_record"
        )

    record = ForecastRecord.from_dict(
        auxiliary["complete_record"]
    )
    if record.case_id != str(d["case_id"]):
        raise ValueError(
            "auxiliary record case_id mismatch"
        )
    if record.label != str(auxiliary["label"]):
        raise ValueError(
            "auxiliary label mismatch"
        )
    if not record.is_valid(
        str(d["evidence_text"]),
        task,
    ):
        raise ValueError(
            "auxiliary complete_record failed validation"
        )

    status = str(qualification.get("status", ""))
    qualified = status in {
        "qualified",
        "conditional",
    }
    supplied_fingerprint = qualification.get(
        "configuration_fingerprint"
    )
    if (
        policy.qualification_required
        and qualified
        and supplied_fingerprint != fingerprint
    ):
        raise ValueError(
            "qualification.configuration_fingerprint mismatch"
        )

    return task, policy, fingerprint


def make_candidate_view(
    d: dict[str, Any],
) -> dict[str, str]:
    deployment = d["deployment_context"]
    return {
        "case_id": str(d["case_id"]),
        "target": str(deployment["target"]),
        "horizon": str(deployment["horizon"]),
        "evidence_contract": str(
            deployment["evidence_contract"]
        ),
        "evidence_text": str(d["evidence_text"]),
    }


def live_case_objects(
    d: dict[str, Any],
    *,
    task_override: dict[str, Any] | None = None,
    policy_override: dict[str, Any] | None = None,
) -> tuple[
    QualificationEvidence,
    ValidatedScope,
    DeploymentContext,
    FrozenFinalizer,
    TaskSpec,
    PolicySpec,
    str,
]:
    task, policy, fingerprint = validate_live_case(
        d,
        task_override=task_override,
        policy_override=policy_override,
    )
    qualification = QualificationEvidence(
        **d["qualification"]
    )
    scope = ValidatedScope(
        **d["validated_scope"]
    )
    deployment = DeploymentContext(
        **d["deployment_context"]
    )
    finalizer = FrozenFinalizer(
        ForecastRecord.from_dict(
            d["auxiliary"]["complete_record"]
        )
    )
    return (
        qualification,
        scope,
        deployment,
        finalizer,
        task,
        policy,
        fingerprint,
    )


def generate_candidates(
    d: dict[str, Any],
    provider: CandidateProvider,
    *,
    task: TaskSpec,
    policy: PolicySpec,
) -> list[ForecastRecord]:
    expected_provider = str(
        d["deployment_context"]["provider"]
    ).lower()
    expected_model = str(
        d["deployment_context"]["backbone"]
    )
    if provider.provider_name != expected_provider:
        raise ValueError(
            "provider adapter does not match deployment"
        )
    if provider.model != expected_model:
        raise ValueError(
            "provider model does not match deployment"
        )

    case_view = make_candidate_view(d)
    records: list[ForecastRecord] = []
    for draw_index in range(
        1,
        policy.draws + 1,
    ):
        record = provider.generate(
            dict(case_view),
            draw_index,
            task,
            policy.draws,
        )
        if record.case_id != str(d["case_id"]):
            raise ValueError(
                f"candidate draw {draw_index} case_id mismatch"
            )
        if not record.is_valid(
            str(d["evidence_text"]),
            task,
        ):
            raise ValueError(
                f"candidate draw {draw_index} failed validation"
            )
        records.append(record)
    return records


def run_live_decision(
    d: dict[str, Any],
    provider: CandidateProvider,
    *,
    task_override: dict[str, Any] | None = None,
    policy_override: dict[str, Any] | None = None,
) -> tuple[list[ForecastRecord], DecisionResult]:
    (
        qualification,
        scope,
        deployment,
        finalizer,
        task,
        policy,
        fingerprint,
    ) = live_case_objects(
        d,
        task_override=task_override,
        policy_override=policy_override,
    )
    candidates = generate_candidates(
        d,
        provider,
        task=task,
        policy=policy,
    )

    result = AgentDecisionHarness().decide(
        candidates=candidates,
        auxiliary_label=str(
            d["auxiliary"]["label"]
        ),
        qualification=qualification,
        validated_scope=scope,
        deployment=deployment,
        evidence_text=str(d["evidence_text"]),
        finalizer=finalizer,
        task=task,
        policy=policy,
        configuration_fingerprint=fingerprint,
    )
    return candidates, result
