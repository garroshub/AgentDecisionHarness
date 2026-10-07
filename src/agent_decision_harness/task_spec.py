from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LabelBand:
    label: str
    min_value: float | None = None
    max_value: float | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True

    def contains(self, value: float) -> bool:
        if self.min_value is not None:
            if value < self.min_value:
                return False
            if value == self.min_value and not self.min_inclusive:
                return False
        if self.max_value is not None:
            if value > self.max_value:
                return False
            if value == self.max_value and not self.max_inclusive:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "min_inclusive": self.min_inclusive,
            "max_inclusive": self.max_inclusive,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LabelBand":
        return cls(
            label=str(d["label"]),
            min_value=None if d.get("min_value") is None else float(d["min_value"]),
            max_value=None if d.get("max_value") is None else float(d["max_value"]),
            min_inclusive=bool(d.get("min_inclusive", True)),
            max_inclusive=bool(d.get("max_inclusive", True)),
        )


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    labels: tuple[str, ...]
    bands: tuple[LabelBand, ...]
    numeric_unit: str = "percentage_points"
    interval_level: float = 0.90
    evidence_exact_match: bool = True

    def validate(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if len(self.labels) < 2 or len(set(self.labels)) != len(self.labels):
            raise ValueError("labels must contain at least two unique values")
        if tuple(band.label for band in self.bands) != self.labels:
            raise ValueError("band labels must match labels in order")
        if not 0.0 < self.interval_level < 1.0:
            raise ValueError("interval_level must be between 0 and 1")
        probes = set()
        for band in self.bands:
            if band.min_value is not None:
                probes.add(band.min_value)
                probes.add(band.min_value - 1e-9)
                probes.add(band.min_value + 1e-9)
            if band.max_value is not None:
                probes.add(band.max_value)
                probes.add(band.max_value - 1e-9)
                probes.add(band.max_value + 1e-9)
        for value in probes:
            matches = [band.label for band in self.bands if band.contains(value)]
            if len(matches) != 1:
                raise ValueError(
                    f"label bands must map each boundary region once; {value} -> {matches}"
                )

    def label_for_point(self, value: float) -> str:
        matches = [band.label for band in self.bands if band.contains(value)]
        if len(matches) != 1:
            raise ValueError(f"point {value} maps to {len(matches)} labels")
        return matches[0]

    def label_contract(self) -> tuple[str, ...]:
        result = []
        for band in self.bands:
            left = "-inf" if band.min_value is None else str(band.min_value)
            right = "+inf" if band.max_value is None else str(band.max_value)
            left_op = "[" if band.min_inclusive else "("
            right_op = "]" if band.max_inclusive else ")"
            result.append(f"{band.label}: {left_op}{left}, {right}{right_op}")
        return tuple(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "labels": list(self.labels),
            "bands": [band.to_dict() for band in self.bands],
            "numeric_unit": self.numeric_unit,
            "interval_level": self.interval_level,
            "evidence_exact_match": self.evidence_exact_match,
        }


DEFAULT_TASK = TaskSpec(
    task_id="postearn_return_v1",
    labels=("negative_reaction", "flat", "positive_reaction"),
    bands=(
        LabelBand("negative_reaction", max_value=-1.0, max_inclusive=False),
        LabelBand("flat", min_value=-1.0, max_value=1.0),
        LabelBand("positive_reaction", min_value=1.0, min_inclusive=False),
    ),
)


def resolve_task(overrides: dict[str, Any] | None = None) -> TaskSpec:
    data = DEFAULT_TASK.to_dict()
    if overrides:
        data.update(overrides)
    labels = tuple(str(x) for x in data["labels"])
    bands = tuple(LabelBand.from_dict(x) for x in data["bands"])
    task = TaskSpec(
        task_id=str(data["task_id"]),
        labels=labels,
        bands=bands,
        numeric_unit=str(data.get("numeric_unit", "percentage_points")),
        interval_level=float(data.get("interval_level", 0.90)),
        evidence_exact_match=bool(data.get("evidence_exact_match", True)),
    )
    task.validate()
    return task
