from __future__ import annotations

import argparse
import json

from .configuration import (
    load_override,
    merge_overrides,
)
from .harness import AgentDecisionHarness
from .io import load_scenario, scenario_objects
from .live import (
    live_case_objects,
    run_live_decision,
    validate_live_case,
)
from .provider_factory import (
    create_provider,
    normalize_provider_name,
)


def _print_record(title, record):
    print(f"\n{title}")
    print(f"  class          {record.label}")
    print(
        f"  point estimate {record.point_estimate:+.2f}"
    )
    print(
        "  interval       "
        f"[{record.interval_lo:+.2f}, "
        f"{record.interval_hi:+.2f}]"
    )
    print(f"  model          {record.model}")
    print(f"  evidence       {record.evidence_quote}")


def replay(
    path: str,
    as_json: bool = False,
) -> int:
    d = load_scenario(path)
    (
        candidates,
        qualification,
        scope,
        deployment,
        finalizer,
    ) = scenario_objects(d)
    result = AgentDecisionHarness().decide(
        candidates=candidates,
        auxiliary_label=d["auxiliary"]["label"],
        qualification=qualification,
        validated_scope=scope,
        deployment=deployment,
        evidence_text=d["evidence_text"],
        finalizer=finalizer,
    )

    if as_json:
        print(
            json.dumps(
                result.to_dict(),
                indent=2,
            )
        )
        return 0

    print("=" * 72)
    print("AgentDecisionHarness")
    print("=" * 72)
    print(f"Case               {d['case_id']}")
    print(f"Task               {deployment.target}")
    print(f"Backbone           {deployment.backbone}")
    print(
        f"Qualification      "
        f"{qualification.status.upper()}"
    )
    print(
        f"Applicability      "
        f"{'PASS' if result.applicability.passed else 'FAIL'}"
    )
    print(
        "LLM votes          "
        + " / ".join(
            result.disagreement.vote_labels
        )
    )
    print(
        f"Auxiliary          "
        f"{result.disagreement.auxiliary_label}"
    )
    print(
        f"Disagreement       "
        f"{result.disagreement.state}"
    )
    print(f"Action             {result.action}")
    print(
        f"Forecast authority {result.authority}"
    )

    _print_record(
        "Baseline complete record",
        result.baseline_record,
    )
    _print_record(
        "Final complete record",
        result.final_record,
    )

    print("\nAudit")
    for key, ok in result.audit.checks.items():
        print(
            f"  {key:<26} "
            f"{'PASS' if ok else 'FAIL'}"
        )

    print("\nDecision trace")
    for item in result.trace:
        print(f"  - {item}")

    expected = d.get("expected")
    if expected:
        observed = {
            "action": result.action,
            "authority": result.authority,
            "final_label": result.final_record.label,
            "audit_passed": result.audit.passed,
        }
        ok = all(
            observed.get(key) == value
            for key, value in expected.items()
        )
        print(
            f"\nFrozen replay check "
            f"{'PASS' if ok else 'FAIL'}"
        )
        if not ok:
            print("Expected:", expected)
            print("Observed:", observed)
            return 2
    return 0


def _load_specs(args):
    task_override = load_override(
        getattr(args, "task_config", None)
    )
    policy_override = load_override(
        getattr(args, "policy_config", None)
    )
    draws = getattr(args, "draws", None)
    if draws is not None:
        policy_override = merge_overrides(
            policy_override,
            {"draws": draws},
        )
    return task_override, policy_override


def show_config(path: str, args) -> int:
    d = load_scenario(path)
    task_override, policy_override = _load_specs(
        args
    )
    task, policy, fingerprint = validate_live_case(
        d,
        task_override=task_override,
        policy_override=policy_override,
    )
    print(
        json.dumps(
            {
                "task": task.to_dict(),
                "policy": policy.to_dict(),
                "configuration_fingerprint": fingerprint,
            },
            indent=2,
        )
    )
    return 0


def live_provider(
    path: str,
    *,
    provider_name: str,
    as_json: bool,
    model: str | None,
    effort: str,
    executable: str | None,
    timeout_seconds: int,
    task_override,
    policy_override,
) -> int:
    d = load_scenario(path)
    (
        _,
        _,
        deployment,
        _,
        task,
        policy,
        fingerprint,
    ) = live_case_objects(
        d,
        task_override=task_override,
        policy_override=policy_override,
    )

    provider_name = normalize_provider_name(
        provider_name
    )
    deployment_provider = normalize_provider_name(
        str(deployment.provider)
    )
    if provider_name != deployment_provider:
        raise ValueError(
            "requested provider does not match live case"
        )

    effective_model = (
        model or deployment.backbone
    )
    if effective_model != deployment.backbone:
        raise ValueError(
            "--model must match "
            "deployment_context.backbone"
        )

    provider = create_provider(
        provider=provider_name,
        model=effective_model,
        effort=effort,
        executable=executable,
        timeout_seconds=timeout_seconds,
    )
    candidates, result = run_live_decision(
        d,
        provider,
        task_override=task_override,
        policy_override=policy_override,
    )

    if as_json:
        print(
            json.dumps(
                {
                    "case_id": d["case_id"],
                    "provider": {
                        "type": provider_name,
                        "model": effective_model,
                        "effort": effort,
                    },
                    "task": task.to_dict(),
                    "policy": policy.to_dict(),
                    "configuration_fingerprint": fingerprint,
                    "candidates": [
                        record.to_dict(
                            task.interval_level
                        )
                        for record in candidates
                    ],
                    "decision": result.to_dict(),
                },
                indent=2,
            )
        )
        return 0

    print("=" * 72)
    print(f"LIVE {provider_name.upper()}")
    print("=" * 72)
    print(f"Task preset        {task.task_id}")
    print(f"Policy preset      {policy.policy_id}")
    print(f"Draws              {policy.draws}")
    print(
        f"Config fingerprint {fingerprint}"
    )
    for index, record in enumerate(
        candidates,
        start=1,
    ):
        _print_record(
            f"Candidate draw {index}",
            record,
        )

    print("\n" + "=" * 72)
    print("AgentDecisionHarness")
    print("=" * 72)
    print(f"Case               {d['case_id']}")
    print(f"Provider           {deployment.provider}")
    print(f"Task               {deployment.target}")
    print(f"Backbone           {deployment.backbone}")
    print(f"Action             {result.action}")
    print(
        f"Forecast authority {result.authority}"
    )
    print(
        f"Disagreement       "
        f"{result.disagreement.state}"
    )

    _print_record(
        "Final complete record",
        result.final_record,
    )

    print("\nAudit")
    for key, ok in result.audit.checks.items():
        print(
            f"  {key:<26} "
            f"{'PASS' if ok else 'FAIL'}"
        )
    return 0


def _add_config_arguments(parser) -> None:
    parser.add_argument(
        "--task-config",
        default=None,
    )
    parser.add_argument(
        "--policy-config",
        default=None,
    )
    parser.add_argument(
        "--draws",
        type=int,
        default=None,
    )


def _add_live_arguments(parser) -> None:
    parser.add_argument("scenario")
    parser.add_argument(
        "--provider",
        required=True,
        choices=("codex", "claude"),
    )
    parser.add_argument(
        "--json",
        action="store_true",
    )
    parser.add_argument(
        "--model",
        default=None,
    )
    parser.add_argument(
        "--effort",
        choices=("low", "medium", "high"),
        default="high",
    )
    parser.add_argument(
        "--executable",
        default=None,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=240,
    )
    _add_config_arguments(parser)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="adh",
        description=(
            "Configurable financial prediction harness"
        ),
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("scenario")
    replay_parser.add_argument(
        "--json",
        action="store_true",
    )

    config_parser = sub.add_parser("config")
    config_parser.add_argument("scenario")
    _add_config_arguments(config_parser)

    live_parser = sub.add_parser("live")
    _add_live_arguments(live_parser)

    args = parser.parse_args(argv)

    if args.command == "replay":
        return replay(
            args.scenario,
            args.json,
        )

    if args.command == "config":
        return show_config(
            args.scenario,
            args,
        )

    if args.command == "live":
        task_override, policy_override = (
            _load_specs(args)
        )
        return live_provider(
            args.scenario,
            provider_name=args.provider,
            as_json=args.json,
            model=args.model,
            effort=args.effort,
            executable=args.executable,
            timeout_seconds=args.timeout_seconds,
            task_override=task_override,
            policy_override=policy_override,
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
