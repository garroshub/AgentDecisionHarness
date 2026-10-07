from __future__ import annotations

import json
import math
from typing import Any, Mapping

from .records import ForecastRecord
from .task_spec import DEFAULT_TASK, TaskSpec

EXPECTED_CANDIDATE_KEYS = {
    "label",
    "point_estimate",
    "interval",
    "evidence_quote",
}


def build_candidate_schema(
    task: TaskSpec = DEFAULT_TASK,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "label",
            "point_estimate",
            "interval",
            "evidence_quote",
        ],
        "properties": {
            "label": {
                "type": "string",
                "enum": list(task.labels),
            },
            "point_estimate": {"type": "number"},
            "interval": {
                "type": "object",
                "additionalProperties": False,
                "required": ["lo", "hi"],
                "properties": {
                    "lo": {"type": "number"},
                    "hi": {"type": "number"},
                },
            },
            "evidence_quote": {
                "type": "string",
                "minLength": 1,
            },
        },
    }


def _unique_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def loads_strict(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def build_candidate_prompt(
    case_view: Mapping[str, Any],
    draw_index: int,
    task: TaskSpec = DEFAULT_TASK,
    draws: int = 3,
) -> str:
    required = {
        "case_id",
        "target",
        "horizon",
        "evidence_contract",
        "evidence_text",
    }
    if set(case_view) != required:
        raise ValueError(
            "candidate case view must contain only "
            + ", ".join(sorted(required))
        )
    if draw_index < 1 or draw_index > draws:
        raise ValueError("draw_index is outside the configured draw range")

    contract = "\n".join(
        f"- {line}"
        for line in task.label_contract()
    )
    return f"""You are an independent forecaster producing candidate draw {draw_index} of {draws}.

Use only the point-in-time evidence packet below. Do not use web search, tools, outside knowledge, later outcomes, or information not present in the packet. Do not infer or request the specialist forecast.

Case ID: {case_view["case_id"]}
Target: {case_view["target"]}
Horizon: {case_view["horizon"]}
Evidence contract: {case_view["evidence_contract"]}
Task: {task.task_id}
Numeric unit: {task.numeric_unit}

Label contract:
{contract}

The interval must contain the point estimate. evidence_quote must be an exact contiguous quote copied from the evidence packet.

Return exactly one JSON object matching the supplied output schema. No prose, Markdown, citations, or extra keys.

POINT-IN-TIME EVIDENCE PACKET
{case_view["evidence_text"]}
"""


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def record_from_candidate_mapping(
    raw: dict[str, Any],
    *,
    case_id: str,
    evidence_text: str,
    model: str,
    source: str,
    draw_index: int,
    provider_label: str,
    task: TaskSpec = DEFAULT_TASK,
) -> ForecastRecord:
    if set(raw) != EXPECTED_CANDIDATE_KEYS:
        missing = sorted(
            EXPECTED_CANDIDATE_KEYS - set(raw)
        )
        extra = sorted(
            set(raw) - EXPECTED_CANDIDATE_KEYS
        )
        raise ValueError(
            f"{provider_label} candidate JSON keys mismatch; "
            f"missing={missing}, extra={extra}"
        )

    interval = raw["interval"]
    if (
        not isinstance(interval, dict)
        or set(interval) != {"lo", "hi"}
    ):
        raise ValueError(
            f"{provider_label} interval must contain exactly lo and hi"
        )
    if (
        not _is_number(raw["point_estimate"])
        or not _is_number(interval["lo"])
        or not _is_number(interval["hi"])
    ):
        raise ValueError(
            f"{provider_label} candidate numeric fields must be finite"
        )
    if (
        not isinstance(raw["label"], str)
        or not isinstance(raw["evidence_quote"], str)
    ):
        raise ValueError(
            f"{provider_label} candidate text fields are invalid"
        )

    record = ForecastRecord(
        case_id=case_id,
        label=raw["label"],
        point_estimate=float(raw["point_estimate"]),
        interval_lo=float(interval["lo"]),
        interval_hi=float(interval["hi"]),
        evidence_quote=raw["evidence_quote"],
        source=source,
        model=model,
        seed=draw_index,
    )
    checks = record.structural_checks(
        evidence_text,
        task,
    )
    if not all(checks.values()):
        failed = [
            name
            for name, ok in checks.items()
            if not ok
        ]
        raise ValueError(
            f"{provider_label} candidate failed validation: "
            + ", ".join(failed)
        )
    return record
