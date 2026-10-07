from __future__ import annotations

from dataclasses import dataclass
from .records import ForecastRecord


@dataclass(frozen=True)
class FrozenFinalizer:
    record: ForecastRecord

    def finalize(self, selected_label: str) -> ForecastRecord:
        if self.record.label != selected_label:
            raise ValueError(
                f"frozen finalizer record label {self.record.label!r} "
                f"does not match selected label {selected_label!r}"
            )
        return self.record
