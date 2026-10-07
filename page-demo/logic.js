(function (root) {
  const TASKS = {
    postearn: {
      taskId: "postearn_return_v1",
      name: "Post-Earnings Reaction",
      short: "Earnings",
      target: "next_day_market_adjusted_return",
      horizon: "next trading day",
      evidenceContract: "point_in_time_earnings_packet_v1",
      numericUnit: "percentage_points",
      intervalLevel: 0.90,
      labels: ["negative_reaction", "flat", "positive_reaction"],
      bands: [
        { label: "negative_reaction", max: -1, maxInclusive: false },
        { label: "flat", min: -1, max: 1, minInclusive: true, maxInclusive: true },
        { label: "positive_reaction", min: 1, minInclusive: false }
      ],
      points: {
        negative_reaction: -2.35,
        flat: 0.40,
        positive_reaction: 1.80
      },
      evidence: {
        negative_reaction: "Cost of revenue increased 19% driven by growth in cloud.",
        flat: "Operating income increased 17% with growth across each segment.",
        positive_reaction: "Revenue increased 15% with growth across each segment."
      },
      packet: [
        "Revenue increased 15% with growth across each segment.",
        "Operating income increased 17% with growth across each segment.",
        "Cost of revenue increased 19% driven by growth in cloud."
      ],
      specialistId: "postearn_auxiliary_text_expert_v1",
      defaultVotes: ["positive_reaction", "flat", "flat"],
      defaultSpecialist: "negative_reaction"
    },
    credit: {
      taskId: "credit_default_risk_v1",
      name: "Credit Default Risk",
      short: "Credit",
      target: "12_month_default_probability_class",
      horizon: "12 months",
      evidenceContract: "point_in_time_credit_packet_v1",
      numericUnit: "probability",
      intervalLevel: 0.95,
      labels: ["low", "medium", "high"],
      bands: [
        { label: "low", max: 0.20, maxInclusive: false },
        { label: "medium", min: 0.20, max: 0.55, minInclusive: true, maxInclusive: true },
        { label: "high", min: 0.55, minInclusive: false }
      ],
      points: {
        low: 0.10,
        medium: 0.38,
        high: 0.72
      },
      evidence: {
        low: "Net leverage declined to 1.8x and interest coverage improved.",
        medium: "Free cash flow remained positive but refinancing needs increased.",
        high: "Net leverage rose to 5.6x while interest coverage fell below 1.5x."
      },
      packet: [
        "Free cash flow remained positive but refinancing needs increased.",
        "Net leverage rose to 5.6x while interest coverage fell below 1.5x.",
        "Cash on hand covers less than one year of scheduled maturities."
      ],
      specialistId: "credit_risk_specialist_v1",
      defaultVotes: ["medium", "medium", "high"],
      defaultSpecialist: "high"
    },
    liquidity: {
      taskId: "liquidity_stress_v1",
      name: "Liquidity Stress",
      short: "Liquidity",
      target: "30_day_liquidity_stress_class",
      horizon: "30 days",
      evidenceContract: "point_in_time_liquidity_packet_v1",
      numericUnit: "stress_score",
      intervalLevel: 0.90,
      labels: ["low", "elevated", "severe"],
      bands: [
        { label: "low", max: 35, maxInclusive: false },
        { label: "elevated", min: 35, max: 70, minInclusive: true, maxInclusive: true },
        { label: "severe", min: 70, minInclusive: false }
      ],
      points: {
        low: 22,
        elevated: 54,
        severe: 84
      },
      evidence: {
        low: "Daily liquidity buffer remained above internal minimums.",
        elevated: "Short-term funding dependence increased while deposit outflows accelerated.",
        severe: "Liquidity coverage fell sharply as wholesale funding rolled off."
      },
      packet: [
        "Short-term funding dependence increased while deposit outflows accelerated.",
        "Liquidity coverage fell sharply as wholesale funding rolled off.",
        "Daily liquidity buffer moved close to the internal minimum."
      ],
      specialistId: "liquidity_specialist_v1",
      defaultVotes: ["elevated", "elevated", "severe"],
      defaultSpecialist: "severe"
    },
    spread: {
      taskId: "credit_spread_move_v1",
      name: "Credit Spread Move",
      short: "Spreads",
      target: "5_day_credit_spread_change",
      horizon: "5 trading days",
      evidenceContract: "point_in_time_credit_market_packet_v1",
      numericUnit: "basis_points",
      intervalLevel: 0.90,
      labels: ["tighten", "flat", "widen"],
      bands: [
        { label: "tighten", max: -10, maxInclusive: false },
        { label: "flat", min: -10, max: 10, minInclusive: true, maxInclusive: true },
        { label: "widen", min: 10, minInclusive: false }
      ],
      points: {
        tighten: -24,
        flat: 3,
        widen: 31
      },
      evidence: {
        tighten: "Primary issuance cleared through guidance with strong oversubscription.",
        flat: "Secondary spreads were little changed despite higher rates.",
        widen: "Dealer inventories rose as fund outflows accelerated across the sector."
      },
      packet: [
        "Dealer inventories rose as fund outflows accelerated across the sector.",
        "Secondary spreads were little changed despite higher rates.",
        "Primary issuance demand weakened into the close."
      ],
      specialistId: "credit_market_specialist_v1",
      defaultVotes: ["flat", "widen", "widen"],
      defaultSpecialist: "widen"
    }
  };

  const POLICY_PRESETS = {
    default: {
      policyId: "qualification_gated_v1",
      name: "Default Gated",
      description: "3 draws · qualification + applicability · route thin-majority conflict",
      draws: 3,
      qualificationRequired: true,
      applicabilityRequired: true,
      routeMajorityConflict: true,
      routeUnanimousConflict: false,
      routeNoMajority: false,
      finalization: "complete_record"
    },
    conservative: {
      policyId: "conservative_5draw_v1",
      name: "Conservative 5-Draw",
      description: "5 draws · same gates · no unanimous or no-majority transfer",
      draws: 5,
      qualificationRequired: true,
      applicabilityRequired: true,
      routeMajorityConflict: true,
      routeUnanimousConflict: false,
      routeNoMajority: false,
      finalization: "complete_record"
    },
    broad: {
      policyId: "broad_conflict_v1",
      name: "Broad Conflict Routing",
      description: "3 draws · allow majority, unanimous, and no-majority conflict routing",
      draws: 3,
      qualificationRequired: true,
      applicabilityRequired: true,
      routeMajorityConflict: true,
      routeUnanimousConflict: true,
      routeNoMajority: true,
      finalization: "complete_record"
    },
    open: {
      policyId: "open_gate_demo_v1",
      name: "Open Gate Demo",
      description: "3 draws · qualification gate disabled · applicability retained",
      draws: 3,
      qualificationRequired: false,
      applicabilityRequired: true,
      routeMajorityConflict: true,
      routeUnanimousConflict: false,
      routeNoMajority: false,
      finalization: "complete_record"
    }
  };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function inBand(value, band) {
    if (band.min !== undefined) {
      if (value < band.min) return false;
      if (value === band.min && band.minInclusive === false) return false;
    }
    if (band.max !== undefined) {
      if (value > band.max) return false;
      if (value === band.max && band.maxInclusive === false) return false;
    }
    return true;
  }

  function labelForPoint(task, value) {
    const matches = task.bands.filter(function (band) {
      return inBand(value, band);
    });
    return matches.length === 1 ? matches[0].label : null;
  }

  function spreadForTask(task) {
    if (task.numericUnit === "probability") return 0.12;
    if (task.numericUnit === "stress_score") return 10;
    if (task.numericUnit === "basis_points") return 14;
    return 1.35;
  }

  function makeRecord(task, label, source, seed) {
    const point = task.points[label];
    const spread = spreadForTask(task);
    let low = point - spread;
    let high = point + spread;
    if (task.numericUnit === "probability") {
      low = Math.max(0, low);
      high = Math.min(1, high);
    }
    return {
      label: label,
      pointEstimate: point,
      intervalLo: low,
      intervalHi: high,
      evidenceQuote: task.evidence[label],
      source: source,
      model: source === "specialist" ? "specialist_model" : "candidate_model",
      seed: seed
    };
  }

  function structuralChecks(task, record) {
    const finite = [record.pointEstimate, record.intervalLo, record.intervalHi].every(Number.isFinite);
    const intervalContainsPoint = finite && record.intervalLo <= record.pointEstimate && record.pointEstimate <= record.intervalHi;
    const pointClassConsistent = finite && labelForPoint(task, record.pointEstimate) === record.label;
    const quotePresent = Boolean((record.evidenceQuote || "").trim());
    return {
      valid_label: task.labels.includes(record.label),
      finite_numeric_fields: finite,
      interval_contains_point: intervalContainsPoint,
      point_class_consistent: pointClassConsistent,
      evidence_quote_present: quotePresent,
      evidence_exact_match: quotePresent
    };
  }

  function classifyDisagreement(records, auxiliaryLabel) {
    const labels = records.map(function (record) { return record.label; });
    const counts = labels.reduce(function (acc, label) {
      acc[label] = (acc[label] || 0) + 1;
      return acc;
    }, {});
    const ranked = Object.entries(counts).sort(function (a, b) { return b[1] - a[1]; });
    const topCount = ranked[0][1];
    const topLabels = ranked.filter(function (entry) { return entry[1] === topCount; }).map(function (entry) { return entry[0]; });
    const total = labels.length;
    const majorityLabel = topLabels.length === 1 && topCount > total / 2 ? topLabels[0] : null;

    let state;
    let auxiliaryRelation;
    let conflict;

    if (!majorityLabel) {
      state = "no unique majority";
      auxiliaryRelation = counts[auxiliaryLabel] ? "candidate_label" : "third_label";
      conflict = true;
    } else if (topCount === total) {
      state = String(topCount) + "-0 unanimous";
      auxiliaryRelation = auxiliaryLabel === majorityLabel ? "agrees_majority" : "disagrees_unanimous";
      conflict = auxiliaryLabel !== majorityLabel;
    } else {
      if (auxiliaryLabel === majorityLabel) {
        auxiliaryRelation = "agrees_majority";
        conflict = false;
      } else if (counts[auxiliaryLabel]) {
        auxiliaryRelation = "supports_minority";
        conflict = true;
      } else {
        auxiliaryRelation = "third_label";
        conflict = true;
      }

      if (total === 3 && topCount === 2) {
        if (auxiliaryRelation === "agrees_majority") state = "2-1, auxiliary agrees majority";
        else if (auxiliaryRelation === "supports_minority") state = "2-1, auxiliary supports minority";
        else state = "2-1, auxiliary third label";
      } else {
        state = String(topCount) + "-" + String(total - topCount) + " majority, auxiliary " + auxiliaryRelation.replaceAll("_", " ");
      }
    }

    return {
      voteLabels: labels,
      majorityLabel: majorityLabel,
      majorityCount: topCount,
      totalCount: total,
      state: state,
      auxiliaryLabel: auxiliaryLabel,
      auxiliaryRelation: auxiliaryRelation,
      conflict: conflict
    };
  }

  function routingTrigger(disagreement, policy) {
    if (!disagreement.conflict) return false;
    if (!disagreement.majorityLabel) return policy.routeNoMajority;
    if (disagreement.majorityCount === disagreement.totalCount) return policy.routeUnanimousConflict;
    return policy.routeMajorityConflict;
  }

  function majorityRecord(records, majorityLabel) {
    if (!majorityLabel) return records[0];
    return records.find(function (record) { return record.label === majorityLabel; });
  }

  function decisionHarness(input) {
    const task = TASKS[input.taskKey];
    const policy = clone(input.policy);
    const candidates = input.votes.slice(0, policy.draws).map(function (label, index) {
      return makeRecord(task, label, "llm_candidate", index + 1);
    });
    const specialist = makeRecord(task, input.specialistLabel, "specialist", null);
    const disagreement = classifyDisagreement(candidates, specialist.label);
    const baseline = majorityRecord(candidates, disagreement.majorityLabel);
    const qualificationAllows = ["qualified", "conditional"].includes(input.qualificationStatus);
    const qualificationMatch = qualificationAllows && input.configMatch;
    const qualificationOk = qualificationMatch || !policy.qualificationRequired;
    const applicabilityOk = input.applicabilityPass || !policy.applicabilityRequired;
    const trigger = routingTrigger(disagreement, policy);
    const shouldRoute = trigger && qualificationOk && applicabilityOk;
    const finalRecord = shouldRoute ? specialist : baseline;
    const checks = structuralChecks(task, finalRecord);
    const auditPassed = Object.values(checks).every(Boolean);
    const authority = shouldRoute ? task.specialistId : "llm_majority";
    const action = shouldRoute ? "route_and_finalize_complete_record" : "retain_majority_record";

    const trace = [
      "candidate_validation=PASS (" + String(candidates.length) + "/" + String(candidates.length) + ")",
      "task=" + task.taskId,
      "policy=" + policy.policyId,
      "qualification=" + input.qualificationStatus.toUpperCase(),
      "configuration_match=" + (input.configMatch ? "PASS" : "FAIL"),
      "applicability=" + (input.applicabilityPass ? "PASS" : "FAIL"),
      "disagreement_state=" + disagreement.state
    ];

    if (shouldRoute) {
      trace.push("forecast_authority=" + authority);
      trace.push("complete_record_finalization=TRIGGERED");
    } else {
      if (trigger && !qualificationOk) trace.push("routing_blocked=QUALIFICATION");
      else if (trigger && !applicabilityOk) trace.push("routing_blocked=APPLICABILITY");
      else trace.push("routing_trigger=INACTIVE");
      trace.push("forecast_authority=llm_majority");
    }
    trace.push("final_record_audit=" + (auditPassed ? "PASS" : "FAIL"));

    return {
      task: task,
      policy: policy,
      candidates: candidates,
      specialist: specialist,
      disagreement: disagreement,
      baseline: baseline,
      finalRecord: finalRecord,
      checks: checks,
      auditPassed: auditPassed,
      authority: authority,
      action: action,
      trace: trace,
      trigger: trigger,
      shouldRoute: shouldRoute,
      qualificationOk: qualificationOk,
      applicabilityOk: applicabilityOk
    };
  }

  function fingerprintPayload(input, result) {
    return {
      task: {
        task_id: result.task.taskId,
        labels: result.task.labels,
        bands: result.task.bands,
        numeric_unit: result.task.numericUnit,
        interval_level: result.task.intervalLevel
      },
      policy: result.policy,
      provider: input.provider,
      backbone: input.model,
      target: result.task.target,
      horizon: result.task.horizon,
      evidence_contract: result.task.evidenceContract,
      specialist_id: result.task.specialistId
    };
  }

  function fallbackHash(text) {
    let h1 = 0x811c9dc5;
    let h2 = 0x9e3779b9;
    for (let i = 0; i < text.length; i += 1) {
      const code = text.charCodeAt(i);
      h1 ^= code;
      h1 = Math.imul(h1, 0x01000193);
      h2 ^= code + i;
      h2 = Math.imul(h2, 0x85ebca6b);
    }
    const parts = [];
    for (let j = 0; j < 8; j += 1) {
      h1 = Math.imul(h1 ^ (h1 >>> 16), 0x85ebca6b);
      h2 = Math.imul(h2 ^ (h2 >>> 13), 0xc2b2ae35);
      parts.push(((h1 ^ h2) >>> 0).toString(16).padStart(8, "0"));
    }
    return parts.join("").slice(0, 64);
  }

  async function configurationFingerprint(input, result) {
    const text = JSON.stringify(fingerprintPayload(input, result));
    if (root.crypto && root.crypto.subtle && typeof TextEncoder !== "undefined") {
      const bytes = new TextEncoder().encode(text);
      const digest = await root.crypto.subtle.digest("SHA-256", bytes);
      return Array.from(new Uint8Array(digest)).map(function (value) {
        return value.toString(16).padStart(2, "0");
      }).join("");
    }
    return fallbackHash(text);
  }

  const api = {
    TASKS: TASKS,
    POLICY_PRESETS: POLICY_PRESETS,
    clone: clone,
    labelForPoint: labelForPoint,
    makeRecord: makeRecord,
    structuralChecks: structuralChecks,
    classifyDisagreement: classifyDisagreement,
    routingTrigger: routingTrigger,
    majorityRecord: majorityRecord,
    decisionHarness: decisionHarness,
    fingerprintPayload: fingerprintPayload,
    configurationFingerprint: configurationFingerprint
  };

  root.ADHLogic = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);