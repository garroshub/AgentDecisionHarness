from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from agent_decision_harness.claude_code_provider import (
    ClaudeCodeProvider,
    parse_claude_candidate_output,
)
from agent_decision_harness.codex_provider import (
    CodexCLIProvider,
    build_candidate_prompt,
    parse_candidate_output,
)
from agent_decision_harness.configuration import (
    case_configuration_fingerprint,
    resolve_specs,
)
from agent_decision_harness.io import load_scenario
from agent_decision_harness.live import (
    generate_candidates,
    make_candidate_view,
    run_live_decision,
    validate_live_case,
)
from agent_decision_harness.provider_factory import (
    create_provider,
    normalize_provider_name,
)
from agent_decision_harness.records import ForecastRecord
from agent_decision_harness.task_spec import DEFAULT_TASK

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE = (
    "Revenue increased 15% with growth across each segment. "
    "Operating income increased 17% year over year."
)


def live_case(
    *,
    provider: str = "codex",
    backbone: str = "gpt-5.6-sol",
) -> dict:
    return {
        "case_id": "LIVE_TEST_001",
        "evidence_text": EVIDENCE,
        "deployment_context": {
            "target": "post_earnings_market_adjusted_return_class",
            "horizon": "next_trading_day_close",
            "evidence_contract": "point_in_time_earnings_excerpt_v1",
            "backbone": backbone,
            "provider": provider,
        },
        "validated_scope": {
            "target": "post_earnings_market_adjusted_return_class",
            "horizon": "next_trading_day_close",
            "evidence_contract": "point_in_time_earnings_excerpt_v1",
            "backbone": backbone,
            "provider": provider,
        },
        "qualification": {
            "specialist_id": "DO_NOT_LEAK_SPECIALIST",
            "status": "not_qualified",
            "evidence_source": "frozen historical qualification",
            "evaluated_task": "post_earnings_market_adjusted_return_class",
            "control": "three_draw_llm_majority",
            "note": "test qualification",
            "provider": provider,
            "backbone": backbone,
        },
        "auxiliary": {
            "label": "negative_reaction",
            "complete_record": {
                "case_id": "LIVE_TEST_001",
                "label": "negative_reaction",
                "point_estimate": -2.0,
                "interval": {"lo": -4.0, "hi": -1.2},
                "evidence_quote": (
                    "Operating income increased 17% year over year."
                ),
                "source": "DO_NOT_LEAK_SPECIALIST",
                "model": "specialist_v1",
                "seed": None,
            },
        },
    }


def qualified_case(
    *,
    provider: str = "codex",
    backbone: str = "gpt-5.6-sol",
) -> dict:
    case = live_case(
        provider=provider,
        backbone=backbone,
    )
    case["qualification"]["status"] = "conditional"
    task, policy = resolve_specs(case)
    case["qualification"]["configuration_fingerprint"] = (
        case_configuration_fingerprint(
            case,
            task,
            policy,
        )
    )
    return case


def record(
    *,
    model: str,
    source: str,
    label: str,
    point: float,
    lo: float,
    hi: float,
    quote: str,
    draw: int,
) -> ForecastRecord:
    return ForecastRecord(
        case_id="LIVE_TEST_001",
        label=label,
        point_estimate=point,
        interval_lo=lo,
        interval_hi=hi,
        evidence_quote=quote,
        source=source,
        model=model,
        seed=draw,
    )


class StubProvider:
    def __init__(
        self,
        provider_name: str,
        model: str,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self.views: list[dict] = []
        self.records = [
            record(
                model=model,
                source=f"{provider_name}_stub",
                label="flat",
                point=0.2,
                lo=-1.0,
                hi=1.0,
                quote=(
                    "Revenue increased 15% with growth across each segment."
                ),
                draw=1,
            ),
            record(
                model=model,
                source=f"{provider_name}_stub",
                label="flat",
                point=0.4,
                lo=-0.8,
                hi=1.0,
                quote=(
                    "Operating income increased 17% year over year."
                ),
                draw=2,
            ),
            record(
                model=model,
                source=f"{provider_name}_stub",
                label="positive_reaction",
                point=1.5,
                lo=0.2,
                hi=2.5,
                quote=(
                    "Revenue increased 15% with growth across each segment."
                ),
                draw=3,
            ),
        ]

    def generate(
        self,
        case_view,
        draw_index,
        task=DEFAULT_TASK,
        draws=3,
    ):
        self.views.append(dict(case_view))
        return self.records[draw_index - 1]


class LiveProviderTests(unittest.TestCase):
    def test_candidate_prompt_is_provider_neutral_and_allowlisted(self):
        case = live_case()
        view = make_candidate_view(case)
        self.assertEqual(
            set(view),
            {
                "case_id",
                "target",
                "horizon",
                "evidence_contract",
                "evidence_text",
            },
        )
        serialized = json.dumps(view)
        self.assertNotIn("DO_NOT_LEAK_SPECIALIST", serialized)
        self.assertNotIn("qualification", serialized)
        self.assertNotIn("auxiliary", serialized)
        self.assertNotIn("codex", serialized)

        prompt = build_candidate_prompt(view, 1)
        self.assertNotIn("DO_NOT_LEAK_SPECIALIST", prompt)
        self.assertNotIn("specialist_v1", prompt)

    def test_live_case_rejects_realized_outcome(self):
        case = live_case()
        case["realized_outcome"] = {"return": 4.2}
        with self.assertRaisesRegex(ValueError, "forbidden field"):
            validate_live_case(case)

    def test_live_case_requires_provider_scoped_qualification(self):
        case = live_case()
        case["qualification"]["provider"] = "claude"
        with self.assertRaisesRegex(ValueError, "qualification.provider"):
            validate_live_case(case)

        case = live_case()
        case["qualification"]["backbone"] = "other-model"
        with self.assertRaisesRegex(ValueError, "qualification.backbone"):
            validate_live_case(case)

    def test_codex_strict_parser_rejects_extra_and_duplicate_keys(self):
        valid = json.dumps(
            {
                "label": "flat",
                "point_estimate": 0.2,
                "interval": {"lo": -1.0, "hi": 1.0},
                "evidence_quote": (
                    "Revenue increased 15% with growth across each segment."
                ),
            }
        )
        parsed = parse_candidate_output(
            valid,
            case_id="LIVE_TEST_001",
            evidence_text=EVIDENCE,
            model="gpt-5.6-sol",
            draw_index=1,
        )
        self.assertTrue(parsed.is_valid(EVIDENCE))

        extra = valid[:-1] + ', "extra": 1}'
        with self.assertRaisesRegex(ValueError, "keys mismatch"):
            parse_candidate_output(
                extra,
                case_id="LIVE_TEST_001",
                evidence_text=EVIDENCE,
                model="gpt-5.6-sol",
                draw_index=1,
            )

        duplicate = (
            '{"label":"flat","label":"flat","point_estimate":0.2,'
            '"interval":{"lo":-1.0,"hi":1.0},'
            '"evidence_quote":"Revenue increased 15% with growth across each segment."}'
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            parse_candidate_output(
                duplicate,
                case_id="LIVE_TEST_001",
                evidence_text=EVIDENCE,
                model="gpt-5.6-sol",
                draw_index=1,
            )

    def test_claude_structured_output_envelope_is_normalized(self):
        envelope = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "structured_output": {
                    "label": "flat",
                    "point_estimate": 0.3,
                    "interval": {"lo": -0.9, "hi": 1.0},
                    "evidence_quote": (
                        "Operating income increased 17% year over year."
                    ),
                },
            }
        )
        parsed = parse_claude_candidate_output(
            envelope,
            case_id="LIVE_TEST_001",
            evidence_text=EVIDENCE,
            model="claude-sonnet-5",
            draw_index=1,
        )
        self.assertEqual(
            parsed.source,
            "claude_code_live",
        )
        self.assertEqual(
            parsed.model,
            "claude-sonnet-5",
        )
        self.assertTrue(parsed.is_valid(EVIDENCE))

    def test_claude_command_is_headless_restricted_and_tool_free(self):
        provider = ClaudeCodeProvider(
            model="claude-sonnet-5",
            effort="high",
        )
        with patch(
            "agent_decision_harness.claude_code_provider._resolve_claude_prefix",
            return_value=["claude"],
        ):
            command = provider._command()

        for flag in (
            "-p",
            "--json-schema",
            "--no-session-persistence",
            "--safe-mode",
            "--restricted",
            "--tools",
            "--disallowedTools",
            "--permission-prompts",
            "--no-chrome",
            "--disable-slash-commands",
        ):
            self.assertIn(flag, command)
        self.assertIn("mcp__*", command)
        tools_index = command.index("--tools")
        self.assertEqual(
            command[tools_index + 1],
            "",
        )

    def test_adapter_identity_must_match_live_case(self):
        case = live_case(
            provider="codex",
            backbone="gpt-5.6-sol",
        )
        task, policy = resolve_specs(case)

        wrong = StubProvider(
            "claude",
            "gpt-5.6-sol",
        )
        with self.assertRaisesRegex(
            ValueError,
            "provider adapter",
        ):
            generate_candidates(
                case,
                wrong,
                task=task,
                policy=policy,
            )

        wrong_model = StubProvider(
            "codex",
            "other-model",
        )
        with self.assertRaisesRegex(
            ValueError,
            "provider model",
        ):
            generate_candidates(
                case,
                wrong_model,
                task=task,
                policy=policy,
            )

    def test_codex_and_claude_use_same_harness_contract(self):
        for provider_name, model in (
            ("codex", "gpt-5.6-sol"),
            ("claude", "claude-sonnet-5"),
        ):
            with self.subTest(provider=provider_name):
                case = qualified_case(
                    provider=provider_name,
                    backbone=model,
                )
                provider = StubProvider(
                    provider_name,
                    model,
                )
                candidates, result = run_live_decision(
                    case,
                    provider,
                )
                self.assertEqual(
                    len(candidates),
                    3,
                )
                self.assertEqual(
                    result.action,
                    "route_and_finalize_complete_record",
                )
                self.assertEqual(
                    result.authority,
                    "DO_NOT_LEAK_SPECIALIST",
                )
                self.assertEqual(
                    result.final_record.label,
                    "negative_reaction",
                )
                self.assertTrue(result.audit.passed)
                self.assertEqual(
                    len(provider.views),
                    3,
                )

    def test_provider_factory_supports_codex_and_claude(self):
        codex = create_provider(
            provider="codex",
            model="gpt-5.6-sol",
        )
        claude = create_provider(
            provider="claude",
            model="claude-sonnet-5",
        )
        self.assertIsInstance(
            codex,
            CodexCLIProvider,
        )
        self.assertIsInstance(
            claude,
            ClaudeCodeProvider,
        )
        self.assertEqual(
            normalize_provider_name("claude"),
            "claude",
        )

    def test_bundled_live_samples_validate(self):
        for name in (
            "sample_postearn_codex.json",
            "sample_postearn_claude.json",
        ):
            case = load_scenario(
                ROOT / "examples" / "live" / name
            )
            validate_live_case(case)


if __name__ == "__main__":
    unittest.main()
