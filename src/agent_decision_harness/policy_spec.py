from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicySpec:
    policy_id: str
    draws: int = 3
    qualification_required: bool = True
    applicability_required: bool = True
    route_majority_conflict: bool = True
    route_unanimous_conflict: bool = False
    route_no_majority: bool = False
    finalization: str = "complete_record"

    def validate(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must be non-empty")
        if self.draws < 1:
            raise ValueError("draws must be at least 1")
        if self.finalization != "complete_record":
            raise ValueError("finalization must be complete_record")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "draws": self.draws,
            "qualification_required": self.qualification_required,
            "applicability_required": self.applicability_required,
            "route_majority_conflict": self.route_majority_conflict,
            "route_unanimous_conflict": self.route_unanimous_conflict,
            "route_no_majority": self.route_no_majority,
            "finalization": self.finalization,
        }


DEFAULT_POLICY = PolicySpec(policy_id="qualification_gated_v1")


def resolve_policy(overrides: dict[str, Any] | None = None) -> PolicySpec:
    data = DEFAULT_POLICY.to_dict()
    if overrides:
        data.update(overrides)
    policy = PolicySpec(
        policy_id=str(data["policy_id"]),
        draws=int(data.get("draws", 3)),
        qualification_required=bool(data.get("qualification_required", True)),
        applicability_required=bool(data.get("applicability_required", True)),
        route_majority_conflict=bool(data.get("route_majority_conflict", True)),
        route_unanimous_conflict=bool(data.get("route_unanimous_conflict", False)),
        route_no_majority=bool(data.get("route_no_majority", False)),
        finalization=str(data.get("finalization", "complete_record")),
    )
    policy.validate()
    return policy
