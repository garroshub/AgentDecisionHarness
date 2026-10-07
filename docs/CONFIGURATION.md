# Configuration

## Default task

    task_id = postearn_return_v1
    labels = negative_reaction, flat, positive_reaction
    negative_reaction < -1.0
    flat = [-1.0, 1.0]
    positive_reaction > 1.0
    numeric_unit = percentage_points
    interval_level = 0.90
    evidence_exact_match = true

## Default policy

    policy_id = qualification_gated_v1
    draws = 3
    qualification_required = true
    applicability_required = true
    route_majority_conflict = true
    route_unanimous_conflict = false
    route_no_majority = false
    finalization = complete_record

## Partial policy override

    {
      "draws": 5
    }

All other policy fields inherit their default values.

## Partial task override

    {
      "task_id": "wide_return_band_v1",
      "bands": [
        {
          "label": "negative_reaction",
          "max_value": -2.0,
          "max_inclusive": false
        },
        {
          "label": "flat",
          "min_value": -2.0,
          "max_value": 2.0
        },
        {
          "label": "positive_reaction",
          "min_value": 2.0,
          "min_inclusive": false
        }
      ]
    }

The labels remain inherited from the default task.

## Fully custom task

A task can replace the label space and bands completely.

    {
      "task_id": "risk_probability_v1",
      "labels": ["low", "medium", "high"],
      "bands": [
        {
          "label": "low",
          "max_value": 0.3,
          "max_inclusive": false
        },
        {
          "label": "medium",
          "min_value": 0.3,
          "max_value": 0.7
        },
        {
          "label": "high",
          "min_value": 0.7,
          "min_inclusive": false
        }
      ],
      "numeric_unit": "probability",
      "interval_level": 0.95
    }

The auxiliary complete record must satisfy the same resolved task.

## Fingerprint

Use:

    python -m agent_decision_harness.cli config <case.json>

Any change to task, policy, provider, backbone, target, horizon, evidence contract, or specialist changes the fingerprint.
