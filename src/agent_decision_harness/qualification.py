from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QualificationStatus = Literal["qualified", "conditional", "not_qualified"]


@dataclass(frozen=True)
class QualificationEvidence:
    specialist_id: str
    status: QualificationStatus
    evidence_source: str
    evaluated_task: str
    control: str
    note: str = ""
    provider: str | None = None
    backbone: str | None = None
    configuration_fingerprint: str | None = None

    @property
    def allows_authority(self) -> bool:
        return self.status in {"qualified", "conditional"}

    def matches_configuration(self, fingerprint: str | None) -> bool:
        if fingerprint is None:
            return True
        return self.configuration_fingerprint == fingerprint
