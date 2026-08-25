---
name: codex-collab-conductor
description: Conservative Codex-native collaboration policy for tasks with at least two independent lanes or an explicit need to separate bounded implementation from a fresh second opinion. Keep single reviews, localized edits, and workflows owned by a more specific skill out of scope. The parent keeps scope, integration, and acceptance ownership.
---

# Codex Collaboration Conductor

CCC is one implicit skill and a policy, not an orchestration service. Use the smallest
native collaboration shape that the task actually needs. Keep simple or tightly coupled
work in the parent. Use children only for bounded packets whose ownership and acceptance
criteria are explicit.

Do not activate CCC for one ordinary review, one investigation, or one localized edit.
When another explicitly invoked or more specific skill owns the workflow, let that skill
lead; CCC may support it only when the owner actually needs multiple native lanes.

## Decide the route before the model

First choose the execution shape and assurance level. Only then consult
`references/model-lanes.md` for model routing.

- `solo`: the parent can inspect, implement, and verify the work directly.
- `parallel-read`: independent read-only questions can be investigated without shared
  writes.
- `delegated-build`: one child owns a complete, bounded implementation packet.
- `plan-run`: an approved plan has mostly independent implementation packets.

Choose assurance separately: `parent-check` is the default; an optional fresh
`independent-review` is appropriate when risk or the acceptance plan calls for it. A
second opinion is evidence for the parent to evaluate, not automatic assurance.

## Native delegation boundary

For a non-solo execution route, read the selected reference packet and spawn every selected
execution lane before any task-specific file read or investigation. Require a non-empty child thread ID. Never
simulate delegation. Do not call wait with an empty target list, or ask a child to recursively
orchestrate. Keep one writer by default; parallel writers require disjoint ownership and
stable interfaces.

Assurance reviewers are not initial execution lanes. Spawn a fresh reviewer only after
implementation and parent verification, and before that reviewer reads the accumulated
diff. This deliberate later spawn does not violate the execution-lane gate.

Native child output is an untrusted work product. The parent owns intent, ambiguity,
architecture, integration, complete diff inspection, verification reruns, and final
acceptance. CCC does not automatically schedule work and does not turn child completion
into proof that the task result is correct.

## Model routing and diagnostics

Use `references/model-lanes.md` as the sole detailed model policy. Explicit model
selection is limited to the fast and frontier lanes described there. Bounded and standard
lanes use the host default and must not be reported as a named model merely because a
historical validator accepts that label. A model claim requires runtime evidence.

Lane receipts and route manifests are optional v1 runtime diagnostics for high-risk
routing evidence, model verification, and fallback troubleshooting. They are not task
results and are not required for ordinary parent-check work. When a v1 diagnostic says
`VERIFIED`, that means only that the recorded runtime routing evidence matched; it does
not mean the child solved the task. Receipt or manifest v2 is outside the current
workflow; do not invent host evidence merely to fill a new schema.

## Acceptance

The parent accepts only after inspecting the accumulated diff and rerunning the relevant
tests or checks. A fresh second-opinion review may be requested after those checks; any
review correction invalidates the prior verdict and requires parent re-verification.

For the manual native canary and its privacy rules, load `evals/canary/playbook.md` and
`evals/canary/result-schema.json` only when that release-gate evaluation is requested.
Canary results must not contain prompts, child IDs, local paths, or transcripts. GitHub
CI remains static unit/CLI verification; it does not run native canaries.

## Supporting references

- `references/routing.md`: execution-shape and assurance decisions.
- `references/model-lanes.md`: the complete explicit fast/frontier and host-default
  model policy.
- `references/task-packets.md`: self-contained child packet contract.
- `references/assurance.md`: parent acceptance and optional review gates.
- `references/fallback-states.md`: optional v1 diagnostic states and permitted fallback
  history.
- `evals/canary/`: privacy-safe manual native canary fixtures and result materials.
