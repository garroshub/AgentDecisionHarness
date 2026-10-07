# AgentDecisionHarness

AgentDecisionHarness controls forecast authority, conditional routing, and complete-record finalization through configurable task and policy contracts.

## Technical report

[Read the technical report](paper/technical_report.pdf): **Agent Harnesses for Evidence-Grounded Financial Prediction: Qualification-Gated Authority and Conditional Routing**, by Garros Gong.

The report studies specialist qualification, conditional routing, and forecast-record consistency across financial prediction tasks. This repository provides a configurable implementation of the decision design and frozen examples for inspecting its behavior.

The default policy uses:

- three independent candidate draws
- qualification-gated authority transfer
- applicability checks
- majority-conflict routing
- complete-record finalization
- evidence and point-class consistency checks

The included tasks are examples. New tasks can be defined through `TaskSpec` as long as the forecast follows the current record contract: discrete label, numeric point estimate, prediction interval, and evidence quote.

## Install

Python 3.11+.

    pip install -e .

## Tests

PowerShell:

    .\run_tests.ps1

Or:

    python -m unittest discover -s tests

## Frozen replay

    .\run_demo.ps1

Direct CLI:

    adh replay examples\frozen\FH025_route.json

## Inspect resolved configuration

    adh config examples\live\sample_postearn_codex.json

This prints the resolved task, resolved policy, and configuration fingerprint.

## Live provider mode

Codex:

    .\run_live_demo.ps1 -Provider codex

Claude Code:

    .\run_live_demo.ps1 -Provider claude

Direct CLI:

    adh live examples\live\sample_postearn_codex.json --provider codex

Live mode requires the selected provider CLI to be installed and authenticated.

## Configuration

Task configuration controls:

- task identity
- label space
- numeric bands
- numeric unit
- interval level
- evidence matching

Policy configuration controls:

- draw count
- qualification gate
- applicability gate
- majority-conflict routing
- unanimous-conflict routing
- no-majority routing
- finalization mode

External JSON files can override only the fields that change. Unspecified fields inherit the defaults.

Examples:

    adh config examples\live\sample_postearn_codex.json --policy-config examples\config\policy_five_draw.json

    adh config examples\live\sample_postearn_codex.json --task-config examples\config\task_wide_return.json

## Qualification fingerprint

Authority qualification is tied to the resolved configuration.

The fingerprint includes:

- task
- policy
- provider
- backbone
- target
- horizon
- evidence contract
- specialist

Changing these inputs changes the qualification identity.

## Data boundary

Candidate providers receive only:

- case ID
- target
- horizon
- evidence contract
- point-in-time evidence

They do not receive specialist output, qualification status, routing state, oracle data, or realized outcomes.

## Page demo

Run locally:

    python -m http.server 8000 --directory page-demo

Then open:

    http://localhost:8000

The page demo is static and does not make live model calls.

## Repository layout

    src/agent_decision_harness/
    examples/
        config/
        live/
        frozen/
    tests/
    docs/
    page-demo/

    pyproject.toml
    run_demo.ps1
    run_live_demo.ps1
    run_tests.ps1

See `docs/` for architecture, configuration, and data contracts.

