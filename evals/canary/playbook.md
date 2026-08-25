# CCC manual native canary playbook

## Gate and privacy rules

This is a manual native release gate. The runner must use a current Codex host and real
native spawn/wait operations where a fixture expects a child. Do not simulate a child,
fabricate routing evidence, or run the package as a benchmark.

All fixture inputs are synthetic and read-only. Before each scenario, record the start
time locally for wall-time measurement; after the scenario, write only the fields in
`result-schema.json`. Record the fixture SHA-256, expected/observed child counts,
distinctness, requested/resolved effort, and whether the repository state remained
identical to its pre-scenario baseline. The baseline may already contain the intended
implementation diff; the canary itself must introduce no change.
Do not copy task prompts, child IDs, local paths, or transcripts
into the result, notes, issue, or release artifact. If a field cannot be observed safely,
use the schema's null/unknown value and set `verification` to `NOT_VERIFIED` where
appropriate.

Run exactly one functional execution per scenario. Do not repeat a scenario to improve a
number. No performance claim is allowed until at least five repeated comparisons against
the same solo baseline have been completed and reviewed separately.

For every non-solo scenario, the parent chooses the execution shape and assurance before
choosing a model. The parent remains responsible for the final task result and any
rework. A child report or a runtime routing observation is not acceptance proof.

## Scenario procedure

### 1. Solo guard

Fixture: `fixtures/solo-guard.json`

Use no native child. Classify the synthetic small, tightly coupled task directly in the
parent. Expected outcome:

- route: `solo`
- requested/resolved model: `null` unless the host exposes an unrelated parent value;
  do not invent one
- task result: `PASS` when the parent keeps the work solo
- verification: `NOT_VERIFIED`; no child routing evidence is expected, and absence of a
  child must not be relabeled as runtime model evidence
- parent rework: the observed coarse value

The scenario fails if the parent spawns a child merely to prove that delegation works.

### 2. Parallel read

Fixture: `fixtures/parallel-read.json`

Create one read-only native packet for each of the two independent synthetic questions.
Spawn the selected lanes before doing the task-specific investigation, wait only on
confirmed child IDs, and have the parent reconcile both answers. Expected outcome:

- route: `parallel-read`
- requested model: `host-default`
- resolved model: observed only when runtime metadata is available
- task result: `PASS` when both independent answers match the fixture's expected values
  and the parent reconciles them
- verification: `VERIFIED` only when the parent has the routing evidence it chose to
  collect; otherwise `NOT_VERIFIED`

Do not add a child count beyond the two fixture lanes and do not claim that parallelism
improved time or correctness.

### 3. Fast route and permitted fallback

Fixture: `fixtures/fast-route-fallback.json`

Use the fast route for the bounded read-only classification. Request the explicit fast
model and low reasoning described in `references/model-lanes.md`. If the host rejects the
request before a child starts because the model is unavailable or quota-denied, retry
exactly once with the permitted explicit fallback. If the child starts and then times
out or returns `child_error`, do not switch models; mark the task/verification outcome
according to the actual evidence.

Expected outcome:

- route: `fast`
- requested model: the primary fast request, even when the permitted fallback is used
- resolved model: the observed model, or null when unavailable
- fallback: `none` or the single permitted fast fallback
- task result: `PASS` only when the synthetic classification is correct
- verification: `VERIFIED` only when the selected runtime evidence is available

Never force an outage, fabricate a quota denial, or call a manually chosen second model
a fallback. One functional run may legitimately take the no-fallback branch.

### 4. Host-default judgment

Fixture: `fixtures/host-default-judgment.json`

Use a standard judgment packet that does not require a concrete explicit model. Leave the
model choice to the Codex host. The parent must not claim a named model from a historical
v1 capability label or from the task shape. Expected outcome:

- route: `standard`
- requested model: `host-default`
- resolved model: the observed host value, or null when the host does not expose it
- fallback: `none`
- task result: `PASS` when the parent correctly identifies the fixture's integration
  decision and reruns the check
- verification: `VERIFIED` only if the observed routing evidence supports the claim;
  otherwise `NOT_VERIFIED`

This scenario tests judgment about when not to force a model, not a named-model
benchmark.

### 5. Frontier seeded-defect review

Fixture: `fixtures/frontier-seeded-defect-review.json`

The fixture contains a tiny synthetic function and an explicit contract. Use the frontier
route only for this concrete seeded-defect review need. Request the Sol route and high
reasoning described in `references/model-lanes.md`; use xhigh only if the parent writes a
specific reason high is insufficient. The parent must compare the review finding with the
fixture contract and rerun the check.

Expected outcome:

- route: `frontier`
- requested model: the explicit Sol request
- resolved model: observed only from runtime metadata
- task result: `PASS` when the review identifies the empty-input defect and the parent
  confirms it against the contract
- verification: `VERIFIED` only with runtime routing evidence
- if the required Sol request is unavailable: no downgrade; record `task_result` as
  `FAIL` and `verification` as `NOT_VERIFIED`

## Result recording

Copy `result-template.json` once per scenario. Fill every field with the observed,
redacted value. `wall_time_ms` is the single functional run's elapsed wall time, not a
throughput claim. `parent_rework` is only the coarse category in the schema. Keep the
result file free of prompts, child IDs, local paths, transcripts, and other execution
details. The parent should review the complete set and state any unavailable proof; the
canary package itself does not declare the policy proven.
