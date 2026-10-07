# Data Contract

## Runtime case

Required fields:

- case_id
- evidence_text
- deployment_context
- validated_scope
- qualification
- auxiliary.label
- auxiliary.complete_record

Optional fields:

- task
- policy

Runtime cases cannot contain realized outcomes, oracle values, pre-generated candidates, or replay expectations.

## Candidate record

Each candidate contains:

- label
- point_estimate
- interval.lo
- interval.hi
- evidence_quote

The resolved TaskSpec determines valid labels and point-to-label consistency.

## Qualification

Qualification contains provider and backbone identity. Qualified and conditional live authority also requires a matching configuration fingerprint when the active policy requires qualification.

## Overrides

External task and policy JSON files are partial overrides. Missing fields inherit from the inline case or built-in defaults.

## Audit

The final record is checked for:

- valid label
- finite numeric fields
- interval containment
- point-label consistency
- non-empty evidence quote
- exact evidence match when enabled by TaskSpec
