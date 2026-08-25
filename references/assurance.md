# Assurance and review

CCC separates collaboration routing from task acceptance. Child output and optional
runtime diagnostics are evidence for the parent to inspect, not an independent proof
system. The repository makes no general speed, correctness, scheduling, or assurance
claim. A single manual canary run according to `evals/canary/playbook.md` proves only the
observed functional route, not a general benefit.

## Parent acceptance

The primary agent always owns:

- User intent and material ambiguity.
- Architecture and interfaces.
- Execution shape and assurance selection.
- Complete diff inspection and changed-file scope.
- Verification reruns and interpretation of their actual output.
- Conflict resolution and final acceptance.

The minimum ordinary acceptance boundary is parent diff inspection plus the relevant test
or check reruns. A lane receipt or route manifest is optional and cannot replace those
checks. If a v1 diagnostic reports `VERIFIED`, that means only that the recorded runtime
routing evidence matched the request; it does not mean the task result is correct.

## Optional independent review

Run a fresh reviewer only after implementation and parent verification when material risk
or the acceptance plan warrants a second opinion. Give the reviewer a fresh context
containing:

- Goal and acceptance criteria.
- Base and target revisions or the accumulated diff.
- Changed-file list.
- Relevant tests and their actual output.
- Known constraints and residual risks.

Do not spawn this reviewer in the initial execution batch. Spawn it after parent
verification and before the reviewer begins inspecting the accumulated diff.

Do not give the reviewer implementation reasoning or self-justification unless a finding
cannot be evaluated without it. The parent adjudicates the result and reruns checks after
any accepted correction.

## Frontier availability

When the acceptance plan requires a frontier Sol route and that requested route is
unavailable, mark the route `NOT_VERIFIED`. Do not silently downgrade it or describe a
parent self-review as the missing frontier evidence. The parent may choose a new,
explicitly declared route, but it must not claim the required frontier gate passed.

## Dual review

Use dual review only when both implementation correctness and architecture boundaries
need independent scrutiny:

- Code lane: correctness, security, regressions, tests, and maintainability.
- Architecture lane: boundaries, interfaces, coupling, migration risk, and long-term
  trade-offs.

The primary agent adjudicates disagreements and verifies every accepted finding before
final acceptance.

## Correction loop

A correction invalidates the prior review verdict. Send a bounded correction packet when
the original context remains useful, or use a fresh implementer when the approach or
specification was materially wrong. Rerun parent verification before another review.
Allow at most two ordinary correction-and-review rounds; after that, reassess the
architecture or requirements and report the unresolved decision.

## Behavioral read-only check

Without an enforced read-only agent profile:

1. Capture repository and relevant artifact state before review.
2. Instruct the reviewer not to modify files or external state.
3. Capture the same state after review.
4. Any mutation invalidates the review and must be disclosed.

The manual native canary is separate from CI and is a release-gate observation, not a
simulation or benchmark. Run one functional execution per scenario and do not claim
performance until at least five repeated comparisons with a solo baseline exist.
