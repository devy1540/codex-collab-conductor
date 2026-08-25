# Routing

Choose the execution shape and assurance independently. Choose both before consulting
`model-lanes.md`; model selection must not decide whether collaboration is warranted.

CCC is a conservative policy. It makes no claim that delegation is faster, more correct,
automatically scheduled, or independently assuring. The parent remains responsible for
the result.

## Execution route

### solo

Use when the task is small, tightly coupled, or cheaper to complete directly than to
explain and integrate.

Typical signals:

- One localized edit or one root cause and code path.
- No genuinely independent read-only questions.
- Shared state makes parallel work unsafe.
- Delegation would repeat the primary agent's required reading.

The solo guard is a valid outcome, not a failed attempt to collaborate.

### parallel-read

Use when at least two questions can be answered without sharing mutable state. Good lanes
include repository ownership mapping, independent failure clusters, documentation versus
local implementation, and read-only security or maintainability checks.

Execution contract:

1. Build one self-contained read-only packet per lane.
2. Spawn every selected lane before task-specific investigation.
3. Confirm a non-empty child ID for each accepted lane.
4. Wait only for confirmed child IDs.
5. If a spawn fails, do not replace it with an empty wait or claim parallel execution.

Do not add parallel lanes merely to reach a fixed child count. Capacity can limit the
active batch; unstarted work stays pending until the parent can safely dispatch it.

### delegated-build

Use one writer when the objective, owned files, interfaces, constraints, and verification
are complete enough that the child should not invent product or architecture decisions.

Do not delegate implementation when material requirements remain unresolved, ownership
cannot be bounded, shared modules require frequent decisions, or the parent would need to
redo the implementation to verify it.

### plan-run

Use for an approved plan with multiple implementation packets. Dispatch a fresh
implementer per slice, normally sequentially. Parallelize only when ownership and
interfaces are disjoint and stable, and the parent can inspect the accumulated diff.

## Assurance route

### parent-check

Default for ordinary work. The parent inspects the complete diff, reruns relevant tests or
checks, reconciles child findings, and accepts or rejects the result.

### independent-review

Optional after implementation and parent verification. Give the fresh reviewer the goal,
acceptance criteria, accumulated diff, changed-file list, actual check output, constraints,
and residual risks. Do not substitute the review for parent verification.

The reviewer is not part of the initial execution-lane batch. Spawn it after parent
verification and before it performs reviewer-specific diff inspection.

### dual-review

Use only when both implementation correctness and architecture boundaries need separate
fresh scrutiny. The parent adjudicates disagreements and verifies every accepted finding.

## Model and diagnostics boundary

After the route is selected, follow `model-lanes.md`. All four capability lanes have
explicit model requests and effort boundaries there. The fast lane has one permitted
pre-child unavailable/quota cross-model fallback; bounded implementation and standard
judgment have no generic retry or implicit model reroute.

Lane receipts and route manifests are optional v1 diagnostics. Use them only when high-risk
routing evidence, model verification, or fallback troubleshooting justifies the privacy
and record-keeping cost. Their `VERIFIED` value means runtime routing evidence only; it
does not prove task-result correctness. No receipt or manifest v2 is part of this policy.

## Route escalation

Escalate when evidence reveals wider blast radius, hidden coupling, security sensitivity,
or an incorrect initial specification. Declare the route change and its reason. Do not
silently downgrade assurance, swap a started child to another model, or treat missing
runtime evidence as a successful route. A bounded child that lacks a material decision
reports `NEEDS_DECISION`; the parent may explicitly reroute it to standard judgment after
reassessing the task shape. A standard child that expands into architecture, security, or
other high-risk judgment stops for parent reassessment, which may explicitly choose the
frontier lane. Neither transition is automatic.
