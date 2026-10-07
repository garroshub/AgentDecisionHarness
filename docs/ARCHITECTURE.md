# Architecture

The harness has four independent layers.

    Provider
       |
       v
    TaskSpec
       |
       v
    PolicySpec
       |
       v
    AgentDecisionHarness

## Provider

Providers only generate candidate records. Codex and Claude Code use the same candidate contract.

## TaskSpec

TaskSpec defines the prediction semantics:

- label space
- numeric bands
- numeric unit
- interval level
- evidence matching

The provider schema and prompt are generated from the resolved TaskSpec.

## PolicySpec

PolicySpec defines decision behavior:

- number of draws
- qualification requirement
- applicability requirement
- majority-conflict routing
- unanimous-conflict routing
- no-majority routing
- complete-record finalization

The built-in defaults reproduce the original three-draw qualification-gated behavior.

## Resolution order

    built-in defaults
        -> case task/policy
        -> external task/policy override
        -> CLI draw override

Only supplied fields replace defaults.

## Qualification

The resolved task and policy are part of the qualification identity. The harness computes a SHA-256 configuration fingerprint from the resolved configuration and deployment identity.

Qualified or conditional authority requires the stored fingerprint to match when the qualification gate is enabled.

## Routing

Disagreement classification supports any positive draw count.

A unique strict majority is detected when the leading label receives more than half of the votes. Policy controls whether majority conflict, unanimous conflict, or no-majority states may route.

## Finalization

Authority transfer uses a complete specialist record. Class-only patching is not supported.
