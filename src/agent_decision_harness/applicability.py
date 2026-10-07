from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidatedScope:
    target: str
    horizon: str
    evidence_contract: str
    backbone: str | None = None
    provider: str | None = None


@dataclass(frozen=True)
class DeploymentContext:
    target: str
    horizon: str
    evidence_contract: str
    backbone: str
    provider: str | None = None


@dataclass(frozen=True)
class ApplicabilityResult:
    passed: bool
    checks: dict[str, bool]
    reasons: tuple[str, ...]


def check_applicability(scope: ValidatedScope, ctx: DeploymentContext) -> ApplicabilityResult:
    checks = {
        "target_match": scope.target == ctx.target,
        "horizon_match": scope.horizon == ctx.horizon,
        "evidence_contract_match": scope.evidence_contract == ctx.evidence_contract,
        "backbone_match": scope.backbone in (None, ctx.backbone),
        "provider_match": scope.provider in (None, ctx.provider),
    }
    reasons = tuple(k for k, ok in checks.items() if not ok)
    return ApplicabilityResult(all(checks.values()), checks, reasons)
