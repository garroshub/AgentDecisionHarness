from __future__ import annotations

from dataclasses import dataclass

from .records import ForecastRecord
from .task_spec import DEFAULT_TASK, TaskSpec


@dataclass(frozen=True)
class AuditResult:
    passed: bool
    checks: dict[str, bool]


def audit_record(
    record: ForecastRecord,
    evidence_text: str,
    task: TaskSpec = DEFAULT_TASK,
) -> AuditResult:
    checks = record.structural_checks(evidence_text, task)
    return AuditResult(passed=all(checks.values()), checks=checks)
