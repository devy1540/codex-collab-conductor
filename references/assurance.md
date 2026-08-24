# Assurance and review

## Parent acceptance

The primary agent always owns:

- User intent and material ambiguity.
- Architecture and interfaces.
- Route and model selection.
- Complete diff inspection.
- Verification reruns.
- Conflict resolution.
- Final acceptance and reporting.

Child self-review and test reports do not replace parent evidence.

Before accepting non-solo work, verify that every required lane's final state is SUCCEEDED and that its final valid attempt contains a child ID and runtime routing evidence. Preserve earlier failed attempts as history.

## Independent review

Run after implementation and parent verification. Give the reviewer a fresh context containing:

- Goal and acceptance criteria.
- Base and target revisions or the accumulated diff.
- Changed-file list.
- Relevant tests and their actual output.
- Known constraints and residual risks.

The reviewer must not receive implementation reasoning or the implementer's self-justification unless a finding cannot be evaluated without it.

## Dual review

Use only for broad or high-risk work:

- Code lane: correctness, security, regressions, tests, maintainability.
- Architecture lane: boundaries, interfaces, coupling, migration risk, long-term tradeoffs.

The primary agent adjudicates disagreements and verifies any accepted finding before changing code.

If a required frontier reviewer cannot spawn or complete, mark the deliverable NOT_VERIFIED. Do not replace it with a lower-capability reviewer or parent self-review while claiming the independent gate passed.

## Correction loop

- A correction invalidates the prior review verdict.
- Send a bounded correction packet to the original implementer when its context remains useful.
- Use a fresh implementer when the original approach or specification was materially wrong.
- Rerun parent verification before re-review.
- Allow at most two ordinary correction-and-review rounds. After that, stop the loop, reassess architecture or requirements, and report the unresolved blocker or decision.

## Behavioral read-only check

Without a custom read-only agent profile:

1. Capture repository and relevant artifact state before review.
2. Instruct the reviewer not to modify files or external state.
3. Capture the same state after review.
4. Any mutation invalidates the review and must be disclosed.
