(function () {
  const logic = window.ADHLogic;
  const TASKS = logic.TASKS;
  const POLICIES = logic.POLICY_PRESETS;

  const els = {
    taskRibbon: document.getElementById("taskRibbon"),
    provider: document.getElementById("providerSelect"),
    model: document.getElementById("modelInput"),
    policyPreset: document.getElementById("policyPreset"),
    qualificationStatus: document.getElementById("qualificationStatus"),
    specialistLabel: document.getElementById("specialistLabel"),
    candidateControls: document.getElementById("candidateControls"),
    candidateCount: document.getElementById("candidateCount"),
    qualificationRequired: document.getElementById("qualificationRequired"),
    applicabilityRequired: document.getElementById("applicabilityRequired"),
    routeMajority: document.getElementById("routeMajority"),
    routeUnanimous: document.getElementById("routeUnanimous"),
    routeNoMajority: document.getElementById("routeNoMajority"),
    configMatch: document.getElementById("configMatch"),
    applicabilityPass: document.getElementById("applicabilityPass"),
    resolvedPolicyName: document.getElementById("resolvedPolicyName"),
    resolvedPolicyDesc: document.getElementById("resolvedPolicyDesc"),
    runButton: document.getElementById("runButton"),
    resetButton: document.getElementById("resetButton"),
    consoleRunId: document.getElementById("consoleRunId"),
    consoleTaskName: document.getElementById("consoleTaskName"),
    dirtyStatus: document.getElementById("dirtyStatus"),
    terminalOutput: document.getElementById("terminalOutput"),
    authority: document.getElementById("authorityValue"),
    finalClass: document.getElementById("finalClass"),
    audit: document.getElementById("auditValue"),
    finalEvidence: document.getElementById("finalEvidence"),
    finalPoint: document.getElementById("finalPoint"),
    finalInterval: document.getElementById("finalInterval"),
    fingerprint: document.getElementById("fingerprintValue"),
    copyFingerprint: document.getElementById("copyFingerprint")
  };

  let activeTaskKey = "postearn";
  let votes = [];
  let runNumber = 0;
  let renderToken = 0;

  function task() {
    return TASKS[activeTaskKey];
  }

  function policyBase() {
    return POLICIES[els.policyPreset.value];
  }

  function isPolicyOverride(base) {
    return (
      els.qualificationRequired.checked !== base.qualificationRequired ||
      els.applicabilityRequired.checked !== base.applicabilityRequired ||
      els.routeMajority.checked !== base.routeMajorityConflict ||
      els.routeUnanimous.checked !== base.routeUnanimousConflict ||
      els.routeNoMajority.checked !== base.routeNoMajority
    );
  }

  function resolvedPolicy() {
    const base = logic.clone(policyBase());
    const overridden = isPolicyOverride(base);
    return {
      policyId: overridden ? base.policyId + "_custom" : base.policyId,
      name: overridden ? base.name + " + override" : base.name,
      description: base.description,
      draws: base.draws,
      qualificationRequired: els.qualificationRequired.checked,
      applicabilityRequired: els.applicabilityRequired.checked,
      routeMajorityConflict: els.routeMajority.checked,
      routeUnanimousConflict: els.routeUnanimous.checked,
      routeNoMajority: els.routeNoMajority.checked,
      finalization: "complete_record"
    };
  }

  function formatNumber(value, unit) {
    if (unit === "probability") return value.toFixed(2);
    if (unit === "stress_score") return value.toFixed(0) + "/100";
    if (unit === "basis_points") {
      const sign = value > 0 ? "+" : value < 0 ? "−" : "";
      return sign + Math.abs(value).toFixed(0) + " bps";
    }
    const sign = value > 0 ? "+" : value < 0 ? "−" : "";
    return sign + Math.abs(value).toFixed(2) + " pp";
  }

  function fillSelect(select, labels, selected) {
    select.innerHTML = "";
    labels.forEach(function (label) {
      const option = document.createElement("option");
      option.value = label;
      option.textContent = label;
      option.selected = label === selected;
      select.appendChild(option);
    });
  }

  function buildTaskRibbon() {
    els.taskRibbon.innerHTML = "";
    Object.entries(TASKS).forEach(function (entry) {
      const key = entry[0];
      const config = entry[1];
      const button = document.createElement("button");
      button.type = "button";
      button.className = "task-chip";
      button.dataset.task = key;
      button.innerHTML =
        '<span>' + config.short.toUpperCase() + '</span>' +
        '<strong>' + config.name + '</strong>' +
        '<small>' + config.horizon + '</small>';
      button.addEventListener("click", function () {
        setTask(key);
      });
      els.taskRibbon.appendChild(button);
    });
  }

  function buildPolicyOptions() {
    els.policyPreset.innerHTML = "";
    Object.entries(POLICIES).forEach(function (entry) {
      const key = entry[0];
      const config = entry[1];
      const option = document.createElement("option");
      option.value = key;
      option.textContent = config.name;
      els.policyPreset.appendChild(option);
    });
  }

  function normalizeVotes(draws) {
    const defaults = task().defaultVotes.slice();
    const middle = task().labels[Math.floor(task().labels.length / 2)];
    while (defaults.length < draws) defaults.push(middle);
    votes = defaults.slice(0, draws);
  }

  function renderCandidateControls() {
    const draws = policyBase().draws;
    const labels = task().labels;
    const middle = labels[Math.floor(labels.length / 2)];

    while (votes.length < draws) votes.push(middle);
    votes = votes.slice(0, draws);
    els.candidateCount.textContent = String(draws) + " draws";
    els.candidateControls.innerHTML = "";

    votes.forEach(function (vote, index) {
      const row = document.createElement("label");
      row.className = "candidate-control";

      const num = document.createElement("span");
      num.textContent = String(index + 1).padStart(2, "0");

      const select = document.createElement("select");
      fillSelect(select, labels, labels.includes(vote) ? vote : middle);
      votes[index] = select.value;
      select.addEventListener("change", function () {
        votes[index] = select.value;
        markDirty();
      });

      row.append(num, select);
      els.candidateControls.appendChild(row);
    });
  }

  function applyPolicyPreset() {
    const base = policyBase();
    els.qualificationRequired.checked = base.qualificationRequired;
    els.applicabilityRequired.checked = base.applicabilityRequired;
    els.routeMajority.checked = base.routeMajorityConflict;
    els.routeUnanimous.checked = base.routeUnanimousConflict;
    els.routeNoMajority.checked = base.routeNoMajority;
    els.resolvedPolicyName.textContent = base.policyId;
    els.resolvedPolicyDesc.textContent = base.description;
    normalizeVotes(base.draws);
    renderCandidateControls();
    markDirty();
  }

  function setTask(key) {
    activeTaskKey = key;
    const current = task();

    document.querySelectorAll(".task-chip").forEach(function (button) {
      button.classList.toggle("active", button.dataset.task === key);
    });

    fillSelect(
      els.specialistLabel,
      current.labels,
      current.defaultSpecialist
    );
    normalizeVotes(policyBase().draws);
    renderCandidateControls();
    els.consoleTaskName.textContent = current.name;
    markDirty();
  }

  function resetCurrent() {
    els.provider.value = "codex";
    els.model.value = "gpt-5.6-sol";
    els.policyPreset.value = "default";
    els.qualificationStatus.value = "conditional";
    els.configMatch.checked = true;
    els.applicabilityPass.checked = true;
    applyPolicyPreset();
    setTask(activeTaskKey);
    runForecast(false);
  }

  function markDirty() {
    els.dirtyStatus.textContent = "CONFIG CHANGED";
    els.dirtyStatus.classList.add("dirty");
  }

  function getInput() {
    return {
      provider: els.provider.value,
      model: els.model.value.trim() || (
        els.provider.value === "claude"
          ? "claude-sonnet-5"
          : "gpt-5.6-sol"
      ),
      taskKey: activeTaskKey,
      policy: resolvedPolicy(),
      votes: votes.slice(),
      specialistLabel: els.specialistLabel.value,
      qualificationStatus: els.qualificationStatus.value,
      configMatch: els.configMatch.checked,
      applicabilityPass: els.applicabilityPass.checked
    };
  }

  function line(kind, text) {
    return { kind: kind, text: text };
  }

  function terminalLines(input, result, fingerprint) {
    const t = result.task;
    const p = result.policy;
    const lines = [
      line("command", "$ adh predict --task " + t.taskId + " --policy " + p.policyId + " --provider " + input.provider),
      line("dim", "[case] target=" + t.target + " horizon=" + t.horizon),
      line("dim", "[evidence] packet=" + t.evidenceContract + " records=" + String(t.packet.length))
    ];

    result.candidates.forEach(function (record, index) {
      lines.push(
        line(
          "candidate",
          "[draw_" + String(index + 1).padStart(2, "0") + "] class=" +
          record.label +
          " point=" + formatNumber(record.pointEstimate, t.numericUnit) +
          " interval=[" +
          formatNumber(record.intervalLo, t.numericUnit) + ", " +
          formatNumber(record.intervalHi, t.numericUnit) +
          "]"
        )
      );
      lines.push(
        line(
          "evidence",
          '          evidence="' + record.evidenceQuote + '"'
        )
      );
    });

    lines.push(
      line("state", "[disagreement] " + result.disagreement.state)
    );
    lines.push(
      line(
        result.qualificationOk ? "pass" : "warn",
        "[qualification] status=" +
        input.qualificationStatus.toUpperCase() +
        " config_match=" +
        (input.configMatch ? "PASS" : "FAIL") +
        " gate=" +
        (p.qualificationRequired ? "ON" : "OFF")
      )
    );
    lines.push(
      line(
        result.applicabilityOk ? "pass" : "warn",
        "[applicability] " +
        (input.applicabilityPass ? "PASS" : "FAIL") +
        " gate=" +
        (p.applicabilityRequired ? "ON" : "OFF")
      )
    );

    if (result.shouldRoute) {
      lines.push(
        line(
          "route",
          "[routing] TRIGGERED action=route_and_finalize_complete_record"
        )
      );
    } else if (result.trigger) {
      lines.push(
        line(
          "warn",
          "[routing] BLOCKED action=retain_majority_record"
        )
      );
    } else {
      lines.push(
        line(
          "dim",
          "[routing] INACTIVE action=retain_majority_record"
        )
      );
    }

    lines.push(
      line("authority", "[authority] " + result.authority)
    );
    lines.push(
      line(
        "final",
        "[final_record] class=" +
        result.finalRecord.label +
        " point=" +
        formatNumber(result.finalRecord.pointEstimate, t.numericUnit) +
        " interval=[" +
        formatNumber(result.finalRecord.intervalLo, t.numericUnit) + ", " +
        formatNumber(result.finalRecord.intervalHi, t.numericUnit) +
        "] source=" +
        (result.shouldRoute ? "specialist" : "llm_majority")
      )
    );
    lines.push(
      line(
        "evidence-final",
        '[authoritative_evidence] "' +
        result.finalRecord.evidenceQuote +
        '"'
      )
    );
    lines.push(
      line(
        result.auditPassed ? "pass" : "warn",
        "[audit] " +
        (result.auditPassed ? "PASS" : "FAIL") +
        " checks=" +
        String(Object.values(result.checks).filter(Boolean).length) +
        "/" +
        String(Object.keys(result.checks).length)
      )
    );
    lines.push(
      line("fingerprint", "[config_fingerprint] " + fingerprint)
    );
    lines.push(
      line("prompt", "adh> _")
    );
    return lines;
  }

  function renderTerminal(lines, animate) {
    renderToken += 1;
    const token = renderToken;
    els.terminalOutput.innerHTML = "";

    function appendOne(item) {
      const row = document.createElement("div");
      row.className = "term-line term-" + item.kind;
      row.textContent = item.text;
      els.terminalOutput.appendChild(row);
      els.terminalOutput.scrollTop = els.terminalOutput.scrollHeight;
    }

    if (!animate) {
      lines.forEach(appendOne);
      return;
    }

    let index = 0;
    function next() {
      if (token !== renderToken) return;
      if (index >= lines.length) return;
      appendOne(lines[index]);
      index += 1;
      setTimeout(next, index < 4 ? 45 : 28);
    }
    next();
  }

  async function runForecast(animate) {
    const input = getInput();
    const result = logic.decisionHarness(input);
    const fingerprint = await logic.configurationFingerprint(input, result);

    runNumber += 1;
    els.consoleRunId.textContent = "RUN_" + String(runNumber).padStart(4, "0");
    els.consoleTaskName.textContent = result.task.name;
    els.dirtyStatus.textContent = "COMPLETE";
    els.dirtyStatus.classList.remove("dirty");

    els.authority.textContent = result.authority;
    els.finalClass.textContent = result.finalRecord.label;
    els.audit.textContent = result.auditPassed ? "PASS" : "FAIL";
    els.audit.classList.toggle("warn", !result.auditPassed);
    els.finalEvidence.textContent = result.finalRecord.evidenceQuote;
    els.finalPoint.textContent =
      "POINT " +
      formatNumber(result.finalRecord.pointEstimate, result.task.numericUnit);
    els.finalInterval.textContent =
      "INTERVAL [" +
      formatNumber(result.finalRecord.intervalLo, result.task.numericUnit) +
      ", " +
      formatNumber(result.finalRecord.intervalHi, result.task.numericUnit) +
      "]";
    els.fingerprint.textContent = fingerprint;

    renderTerminal(
      terminalLines(input, result, fingerprint),
      animate !== false
    );
  }

  buildTaskRibbon();
  buildPolicyOptions();

  els.policyPreset.value = "default";
  applyPolicyPreset();
  setTask("postearn");

  els.policyPreset.addEventListener("change", function () {
    applyPolicyPreset();
  });

  els.provider.addEventListener("change", function () {
    els.model.value = els.provider.value === "claude"
      ? "claude-sonnet-5"
      : "gpt-5.6-sol";
    markDirty();
  });

  [
    els.model,
    els.qualificationStatus,
    els.specialistLabel,
    els.qualificationRequired,
    els.applicabilityRequired,
    els.routeMajority,
    els.routeUnanimous,
    els.routeNoMajority,
    els.configMatch,
    els.applicabilityPass
  ].forEach(function (element) {
    element.addEventListener(
      element.type === "text" ? "input" : "change",
      function () {
        const base = policyBase();
        els.resolvedPolicyName.textContent =
          resolvedPolicy().policyId;
        els.resolvedPolicyDesc.textContent = base.description;
        markDirty();
      }
    );
  });

  els.runButton.addEventListener("click", function () {
    runForecast(true);
  });

  els.resetButton.addEventListener("click", function () {
    resetCurrent();
  });

  els.copyFingerprint.addEventListener("click", async function () {
    try {
      await navigator.clipboard.writeText(els.fingerprint.textContent);
      els.copyFingerprint.textContent = "COPIED";
      setTimeout(function () {
        els.copyFingerprint.textContent = "COPY";
      }, 1000);
    } catch (error) {
      els.copyFingerprint.textContent = "SELECT";
    }
  });

  runForecast(false);
})();