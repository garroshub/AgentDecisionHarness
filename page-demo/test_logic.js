const L = require("./logic.js");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function input(taskKey, policyKey) {
  const task = L.TASKS[taskKey];
  const policy = L.clone(L.POLICY_PRESETS[policyKey]);
  const votes = task.defaultVotes.slice();
  while (votes.length < policy.draws) {
    votes.push(task.labels[Math.floor(task.labels.length / 2)]);
  }
  return {
    provider: "codex",
    model: "gpt-5.6-sol",
    taskKey: taskKey,
    policy: policy,
    votes: votes.slice(0, policy.draws),
    specialistLabel: task.defaultSpecialist,
    qualificationStatus: "conditional",
    configMatch: true,
    applicabilityPass: true
  };
}

let r = L.decisionHarness(input("postearn", "default"));
assert(r.action === "route_and_finalize_complete_record", "postearn default routing");
assert(r.authority === "postearn_auxiliary_text_expert_v1", "postearn authority");
assert(r.finalRecord.label === "negative_reaction", "postearn final class");
assert(r.auditPassed, "postearn audit");

r = L.decisionHarness(input("credit", "default"));
assert(r.task.taskId === "credit_default_risk_v1", "credit task");
assert(r.auditPassed, "credit audit");

r = L.decisionHarness(input("liquidity", "default"));
assert(r.task.taskId === "liquidity_stress_v1", "liquidity task");
assert(r.auditPassed, "liquidity audit");

r = L.decisionHarness(input("spread", "default"));
assert(r.task.taskId === "credit_spread_move_v1", "spread task");
assert(r.auditPassed, "spread audit");

const conservative = input("credit", "conservative");
assert(conservative.policy.draws === 5, "five draw policy");
r = L.decisionHarness(conservative);
assert(r.candidates.length === 5, "five candidate records");
assert(r.auditPassed, "five draw audit");

const blocked = input("postearn", "default");
blocked.configMatch = false;
r = L.decisionHarness(blocked);
assert(r.action === "retain_majority_record", "qualification mismatch blocks");
assert(r.trace.includes("routing_blocked=QUALIFICATION"), "qualification trace");

const open = input("postearn", "open");
open.qualificationStatus = "not_qualified";
open.configMatch = false;
r = L.decisionHarness(open);
assert(r.action === "route_and_finalize_complete_record", "open gate routes without qualification");

const broad = input("postearn", "broad");
broad.votes = ["flat", "flat", "flat"];
broad.specialistLabel = "positive_reaction";
r = L.decisionHarness(broad);
assert(r.disagreement.state === "3-0 unanimous", "unanimous state");
assert(r.action === "route_and_finalize_complete_record", "broad policy routes unanimous conflict");

const noMajority = input("postearn", "broad");
noMajority.votes = ["negative_reaction", "flat", "positive_reaction"];
noMajority.specialistLabel = "positive_reaction";
r = L.decisionHarness(noMajority);
assert(r.disagreement.majorityLabel === null, "no majority detected");
assert(r.action === "route_and_finalize_complete_record", "broad policy routes no-majority");

console.log("PAGE_LOGIC_ACCEPTANCE=PASS");