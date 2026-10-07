from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .policy_spec import PolicySpec, resolve_policy
from .task_spec import TaskSpec, resolve_task


def load_override(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("configuration override must be a JSON object")
    return data


def merge_overrides(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not base and not override:
        return None
    result = dict(base or {})
    result.update(override or {})
    return result


def resolve_specs(
    case: dict[str, Any],
    *,
    task_override: dict[str, Any] | None = None,
    policy_override: dict[str, Any] | None = None,
) -> tuple[TaskSpec, PolicySpec]:
    task = resolve_task(merge_overrides(case.get("task"), task_override))
    policy = resolve_policy(merge_overrides(case.get("policy"), policy_override))
    return task, policy


def configuration_fingerprint(
    *,
    task: TaskSpec,
    policy: PolicySpec,
    provider: str,
    backbone: str,
    target: str,
    horizon: str,
    evidence_contract: str,
    specialist_id: str,
) -> str:
    payload = {
        "task": task.to_dict(),
        "policy": policy.to_dict(),
        "provider": provider,
        "backbone": backbone,
        "target": target,
        "horizon": horizon,
        "evidence_contract": evidence_contract,
        "specialist_id": specialist_id,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def case_configuration_fingerprint(
    case: dict[str, Any],
    task: TaskSpec,
    policy: PolicySpec,
) -> str:
    deployment = case["deployment_context"]
    qualification = case["qualification"]
    return configuration_fingerprint(
        task=task,
        policy=policy,
        provider=str(deployment["provider"]),
        backbone=str(deployment["backbone"]),
        target=str(deployment["target"]),
        horizon=str(deployment["horizon"]),
        evidence_contract=str(deployment["evidence_contract"]),
        specialist_id=str(qualification["specialist_id"]),
    )
