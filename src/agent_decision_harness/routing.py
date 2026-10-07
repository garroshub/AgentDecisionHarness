from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .policy_spec import DEFAULT_POLICY, PolicySpec
from .records import ForecastRecord


@dataclass(frozen=True)
class DisagreementState:
    vote_labels: tuple[str, ...]
    majority_label: str | None
    majority_count: int
    total_count: int
    state: str
    auxiliary_label: str
    auxiliary_relation: str
    conflict: bool


def classify_disagreement(
    candidates: list[ForecastRecord],
    auxiliary_label: str,
) -> DisagreementState:
    if not candidates:
        raise ValueError("at least one candidate record is required")

    labels = tuple(record.label for record in candidates)
    counts = Counter(labels)
    ranked = counts.most_common()
    top_count = ranked[0][1]
    top_labels = [label for label, count in ranked if count == top_count]
    total = len(labels)
    majority_label = (
        top_labels[0]
        if len(top_labels) == 1 and top_count > total / 2
        else None
    )

    if majority_label is None:
        state = "no unique majority"
        relation = (
            "candidate_label"
            if auxiliary_label in counts
            else "third_label"
        )
        conflict = True
    elif top_count == total:
        state = f"{top_count}-0 unanimous"
        relation = (
            "agrees_majority"
            if auxiliary_label == majority_label
            else "disagrees_unanimous"
        )
        conflict = auxiliary_label != majority_label
    else:
        if auxiliary_label == majority_label:
            relation = "agrees_majority"
            conflict = False
        elif auxiliary_label in counts:
            relation = "supports_minority"
            conflict = True
        else:
            relation = "third_label"
            conflict = True

        if total == 3 and top_count == 2:
            if relation == "agrees_majority":
                state = "2-1, auxiliary agrees majority"
            elif relation == "supports_minority":
                state = "2-1, auxiliary supports minority"
            else:
                state = "2-1, auxiliary third label"
        else:
            state = (
                f"{top_count}-{total - top_count} majority, "
                f"auxiliary {relation.replace('_', ' ')}"
            )

    return DisagreementState(
        vote_labels=labels,
        majority_label=majority_label,
        majority_count=top_count,
        total_count=total,
        state=state,
        auxiliary_label=auxiliary_label,
        auxiliary_relation=relation,
        conflict=conflict,
    )


def routing_trigger(
    disagreement: DisagreementState,
    policy: PolicySpec = DEFAULT_POLICY,
) -> bool:
    if not disagreement.conflict:
        return False
    if disagreement.majority_label is None:
        return policy.route_no_majority
    if disagreement.majority_count == disagreement.total_count:
        return policy.route_unanimous_conflict
    return policy.route_majority_conflict


def majority_record(
    candidates: list[ForecastRecord],
    majority_label: str | None,
) -> ForecastRecord:
    if majority_label is None:
        return candidates[0]
    return next(record for record in candidates if record.label == majority_label)
