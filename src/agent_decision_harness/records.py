from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any

from .task_spec import DEFAULT_TASK, TaskSpec


def label_from_point(point: float, task: TaskSpec = DEFAULT_TASK) -> str:
    return task.label_for_point(point)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass(frozen=True)
class ForecastRecord:
    case_id: str
    label: str
    point_estimate: float
    interval_lo: float
    interval_hi: float
    evidence_quote: str
    source: str
    model: str
    seed: int | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ForecastRecord":
        interval = d.get("interval", {})
        return cls(
            case_id=str(d.get("case_id") or d.get("entity_id")),
            label=str(d["label"]),
            point_estimate=float(d.get("point_estimate", d.get("point_forecast"))),
            interval_lo=float(interval.get("lo", d.get("interval_lo"))),
            interval_hi=float(interval.get("hi", d.get("interval_hi"))),
            evidence_quote=str(d["evidence_quote"]),
            source=str(d.get("source", "candidate")),
            model=str(d.get("model", "unknown")),
            seed=d.get("seed"),
        )

    def structural_checks(
        self,
        evidence_text: str | None = None,
        task: TaskSpec = DEFAULT_TASK,
    ) -> dict[str, bool]:
        finite = all(
            math.isfinite(float(v))
            for v in (self.point_estimate, self.interval_lo, self.interval_hi)
        )
        interval_contains_point = (
            finite and self.interval_lo <= self.point_estimate <= self.interval_hi
        )
        try:
            expected_label = task.label_for_point(self.point_estimate)
        except ValueError:
            expected_label = None
        point_class_consistent = finite and expected_label == self.label
        quote_present = bool(self.evidence_quote.strip())
        evidence_exact = True
        if evidence_text is not None and task.evidence_exact_match:
            evidence_exact = (
                quote_present
                and _norm(self.evidence_quote) in _norm(evidence_text)
            )
        return {
            "valid_label": self.label in task.labels,
            "finite_numeric_fields": finite,
            "interval_contains_point": interval_contains_point,
            "point_class_consistent": point_class_consistent,
            "evidence_quote_present": quote_present,
            "evidence_exact_match": evidence_exact,
        }

    def is_valid(
        self,
        evidence_text: str | None = None,
        task: TaskSpec = DEFAULT_TASK,
    ) -> bool:
        return all(self.structural_checks(evidence_text, task).values())

    def to_dict(
        self,
        interval_level: float = 0.90,
    ) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "label": self.label,
            "point_estimate": self.point_estimate,
            "interval": {
                "level": interval_level,
                "lo": self.interval_lo,
                "hi": self.interval_hi,
            },
            "evidence_quote": self.evidence_quote,
            "source": self.source,
            "model": self.model,
            "seed": self.seed,
        }
