from __future__ import annotations

import unittest

from agent_decision_harness.policy_spec import resolve_policy
from agent_decision_harness.records import ForecastRecord
from agent_decision_harness.routing import (
    classify_disagreement,
    routing_trigger,
)


def rec(label: str, seed: int) -> ForecastRecord:
    points = {
        "negative_reaction": -2.0,
        "flat": 0.0,
        "positive_reaction": 2.0,
    }
    point = points[label]
    return ForecastRecord(
        case_id="P",
        label=label,
        point_estimate=point,
        interval_lo=point - 0.5,
        interval_hi=point + 0.5,
        evidence_quote="e",
        source="test",
        model="test",
        seed=seed,
    )


class PolicyRoutingTests(unittest.TestCase):
    def test_majority_conflict_default_routes(self):
        state = classify_disagreement(
            [
                rec("flat", 1),
                rec("flat", 2),
                rec("positive_reaction", 3),
            ],
            "positive_reaction",
        )
        self.assertTrue(
            routing_trigger(
                state,
                resolve_policy(),
            )
        )

    def test_unanimous_conflict_is_configurable(self):
        state = classify_disagreement(
            [
                rec("flat", 1),
                rec("flat", 2),
                rec("flat", 3),
            ],
            "positive_reaction",
        )
        self.assertFalse(
            routing_trigger(
                state,
                resolve_policy(),
            )
        )
        self.assertTrue(
            routing_trigger(
                state,
                resolve_policy(
                    {
                        "route_unanimous_conflict": True,
                    }
                ),
            )
        )

    def test_no_majority_is_configurable(self):
        state = classify_disagreement(
            [
                rec("negative_reaction", 1),
                rec("flat", 2),
                rec("positive_reaction", 3),
            ],
            "positive_reaction",
        )
        self.assertFalse(
            routing_trigger(
                state,
                resolve_policy(),
            )
        )
        self.assertTrue(
            routing_trigger(
                state,
                resolve_policy(
                    {
                        "route_no_majority": True,
                    }
                ),
            )
        )


if __name__ == "__main__":
    unittest.main()
