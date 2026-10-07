from __future__ import annotations

from pathlib import Path
import unittest

from agent_decision_harness.harness import AgentDecisionHarness
from agent_decision_harness.io import load_scenario, scenario_objects
from agent_decision_harness.records import ForecastRecord

ROOT = Path(__file__).resolve().parents[1]


def run_case(name: str):
    d = load_scenario(ROOT / "examples" / "frozen" / name)
    candidates, qualification, scope, deployment, finalizer = scenario_objects(d)
    return d, AgentDecisionHarness().decide(
        candidates=candidates,
        auxiliary_label=d["auxiliary"]["label"],
        qualification=qualification,
        validated_scope=scope,
        deployment=deployment,
        evidence_text=d["evidence_text"],
        finalizer=finalizer,
    )


class HarnessTests(unittest.TestCase):
    def test_routes_thin_majority_when_authority_is_allowed(self):
        _, result = run_case("FH025_route.json")
        self.assertEqual(result.action, "route_and_finalize_complete_record")
        self.assertEqual(result.final_record.label, "negative_reaction")
        self.assertTrue(result.audit.passed)

    def test_keeps_unanimous_llm_consensus(self):
        _, result = run_case("FH002_consensus.json")
        self.assertEqual(result.action, "retain_majority_record")
        self.assertEqual(result.authority, "llm_majority")
        self.assertTrue(result.audit.passed)

    def test_class_only_patch_breaks_point_class_consistency(self):
        d, result = run_case("FH025_route.json")
        patched = ForecastRecord(
            case_id=result.baseline_record.case_id,
            label=d["auxiliary"]["label"],
            point_estimate=result.baseline_record.point_estimate,
            interval_lo=result.baseline_record.interval_lo,
            interval_hi=result.baseline_record.interval_hi,
            evidence_quote=result.baseline_record.evidence_quote,
            source="class_only_patch",
            model=result.baseline_record.model,
            seed=result.baseline_record.seed,
        )
        self.assertFalse(
            patched.structural_checks(d["evidence_text"])["point_class_consistent"]
        )


if __name__ == "__main__":
    unittest.main()
