from __future__ import annotations

import copy
import unittest

from agent_decision_harness.configuration import (
    case_configuration_fingerprint,
    resolve_specs,
)
from agent_decision_harness.live import (
    run_live_decision,
    validate_live_case,
)
from agent_decision_harness.records import ForecastRecord
from agent_decision_harness.task_spec import (
    DEFAULT_TASK,
    resolve_task,
)

EVIDENCE = (
    "Risk score increased to 0.82 after the latest filing. "
    "Liquidity remained stable during the quarter."
)


def custom_case() -> dict:
    return {
        "case_id": "GENERIC_001",
        "evidence_text": EVIDENCE,
        "deployment_context": {
            "target": "risk_probability",
            "horizon": "30_days",
            "evidence_contract": "point_in_time_risk_packet_v1",
            "backbone": "gpt-5.6-sol",
            "provider": "codex",
        },
        "validated_scope": {
            "target": "risk_probability",
            "horizon": "30_days",
            "evidence_contract": "point_in_time_risk_packet_v1",
            "backbone": "gpt-5.6-sol",
            "provider": "codex",
        },
        "task": {
            "task_id": "risk_probability_v1",
            "labels": ["low", "medium", "high"],
            "bands": [
                {
                    "label": "low",
                    "min_value": None,
                    "max_value": 0.3,
                    "max_inclusive": False,
                },
                {
                    "label": "medium",
                    "min_value": 0.3,
                    "max_value": 0.7,
                },
                {
                    "label": "high",
                    "min_value": 0.7,
                    "max_value": None,
                    "min_inclusive": False,
                },
            ],
            "numeric_unit": "probability",
            "interval_level": 0.95,
        },
        "policy": {
            "policy_id": "five_draw_risk_v1",
            "draws": 5,
        },
        "qualification": {
            "specialist_id": "risk_specialist_v1",
            "status": "conditional",
            "evidence_source": "frozen historical qualification",
            "evaluated_task": "risk_probability",
            "control": "five_draw_majority",
            "note": "",
            "provider": "codex",
            "backbone": "gpt-5.6-sol",
        },
        "auxiliary": {
            "label": "high",
            "complete_record": {
                "case_id": "GENERIC_001",
                "label": "high",
                "point_estimate": 0.9,
                "interval": {
                    "lo": 0.75,
                    "hi": 0.98,
                },
                "evidence_quote": (
                    "Risk score increased to 0.82 after the latest filing."
                ),
                "source": "risk_specialist_v1",
                "model": "risk_specialist_model",
                "seed": None,
            },
        },
    }


def qualified_custom_case() -> dict:
    case = custom_case()
    task, policy = resolve_specs(case)
    case["qualification"]["configuration_fingerprint"] = (
        case_configuration_fingerprint(
            case,
            task,
            policy,
        )
    )
    return case


class FiveDrawProvider:
    provider_name = "codex"
    model = "gpt-5.6-sol"

    def __init__(self) -> None:
        self.records = [
            ForecastRecord(
                "GENERIC_001",
                "medium",
                0.55,
                0.4,
                0.65,
                "Liquidity remained stable during the quarter.",
                "stub",
                self.model,
                1,
            ),
            ForecastRecord(
                "GENERIC_001",
                "medium",
                0.6,
                0.45,
                0.68,
                "Liquidity remained stable during the quarter.",
                "stub",
                self.model,
                2,
            ),
            ForecastRecord(
                "GENERIC_001",
                "medium",
                0.62,
                0.5,
                0.69,
                "Liquidity remained stable during the quarter.",
                "stub",
                self.model,
                3,
            ),
            ForecastRecord(
                "GENERIC_001",
                "high",
                0.82,
                0.72,
                0.92,
                "Risk score increased to 0.82 after the latest filing.",
                "stub",
                self.model,
                4,
            ),
            ForecastRecord(
                "GENERIC_001",
                "high",
                0.85,
                0.74,
                0.95,
                "Risk score increased to 0.82 after the latest filing.",
                "stub",
                self.model,
                5,
            ),
        ]

    def generate(
        self,
        case_view,
        draw_index,
        task,
        draws,
    ):
        if draws != 5:
            raise ValueError("unexpected draw count")
        return self.records[draw_index - 1]


class ConfigurationTests(unittest.TestCase):
    def test_default_specs_preserve_current_rules(self):
        task, policy = resolve_specs({})
        self.assertEqual(
            task,
            DEFAULT_TASK,
        )
        self.assertEqual(
            policy.draws,
            3,
        )
        self.assertTrue(
            policy.qualification_required
        )
        self.assertTrue(
            policy.applicability_required
        )
        self.assertTrue(
            policy.route_majority_conflict
        )

    def test_partial_policy_override_inherits_defaults(self):
        _, policy = resolve_specs(
            {
                "policy": {
                    "draws": 5,
                }
            }
        )
        self.assertEqual(
            policy.draws,
            5,
        )
        self.assertTrue(
            policy.qualification_required
        )
        self.assertTrue(
            policy.applicability_required
        )
        self.assertEqual(
            policy.finalization,
            "complete_record",
        )

    def test_task_override_changes_thresholds(self):
        task = resolve_task(
            {
                "task_id": "wide_band",
                "bands": [
                    {
                        "label": "negative_reaction",
                        "max_value": -2.0,
                        "max_inclusive": False,
                    },
                    {
                        "label": "flat",
                        "min_value": -2.0,
                        "max_value": 2.0,
                    },
                    {
                        "label": "positive_reaction",
                        "min_value": 2.0,
                        "min_inclusive": False,
                    },
                ],
            }
        )
        self.assertEqual(
            task.label_for_point(1.5),
            "flat",
        )
        self.assertEqual(
            task.label_for_point(2.5),
            "positive_reaction",
        )

    def test_configuration_change_invalidates_qualification(self):
        case = qualified_custom_case()
        validate_live_case(case)

        changed = copy.deepcopy(case)
        changed["policy"]["draws"] = 7
        with self.assertRaisesRegex(
            ValueError,
            "configuration_fingerprint mismatch",
        ):
            validate_live_case(changed)

    def test_custom_five_draw_harness_routes_complete_record(self):
        case = qualified_custom_case()
        provider = FiveDrawProvider()
        candidates, result = run_live_decision(
            case,
            provider,
        )
        self.assertEqual(
            len(candidates),
            5,
        )
        self.assertEqual(
            result.policy.draws,
            5,
        )
        self.assertEqual(
            result.task.task_id,
            "risk_probability_v1",
        )
        self.assertEqual(
            result.disagreement.majority_label,
            "medium",
        )
        self.assertEqual(
            result.disagreement.auxiliary_relation,
            "supports_minority",
        )
        self.assertEqual(
            result.action,
            "route_and_finalize_complete_record",
        )
        self.assertEqual(
            result.authority,
            "risk_specialist_v1",
        )
        self.assertEqual(
            result.final_record.label,
            "high",
        )
        self.assertTrue(
            result.audit.passed
        )

    def test_qualification_gate_can_be_disabled(self):
        case = custom_case()
        case["qualification"]["status"] = "not_qualified"
        case["policy"]["qualification_required"] = False
        provider = FiveDrawProvider()
        _, result = run_live_decision(
            case,
            provider,
        )
        self.assertEqual(
            result.action,
            "route_and_finalize_complete_record",
        )
        self.assertEqual(
            result.authority,
            "risk_specialist_v1",
        )


if __name__ == "__main__":
    unittest.main()
