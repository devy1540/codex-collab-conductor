# Model lanes

This file is the sole detailed model policy for CCC. Choose the task shape and the
assurance route before choosing a model. Model names below are explicit request values,
not proof that a host resolved to that model; only allowlisted runtime metadata can prove
resolution.

## Fast lane

Use the fast lane for bounded, read-heavy exploration such as repository search, symbol
mapping, log classification, large-input triage, and formatting review.

- Request `gpt-5.3-codex-spark` with reasoning effort `low` explicitly.
- If and only if the child cannot start because the explicitly requested model is
  unavailable or the host reports a pre-child quota denial, make exactly one
  cross-model fallback attempt with `gpt-5.6-luna` and reasoning effort `low`
  explicitly.
- The Luna/low fallback is exactly one Spark-to-Luna fallback attempt after the primary
  request is rejected before child start. It is not a general retry budget: do not retry
  Luna/low repeatedly, add another model, or use it after a child has started.
- Do not switch models after a Spark child has started and then times out or reports a
  child error. Report the lane failure or change the task route explicitly; do not call
  that event a fast fallback.
- Do not change a global default to obtain Spark. Route this lane per spawn call.

The pre-child fallback is a resilience rule, not a speed or quality claim. The optional
v1 diagnostic records a host-reported pre-child quota rejection as `quota_denied`; do not
infer or invent that cause from a timeout or child error.

## Bounded implementation lane

Use bounded implementation only when the packet is decision-complete: its objective,
owned files, interfaces, constraints, and verification are explicit enough that the child
can implement without inventing product or architecture decisions.

- Request `gpt-5.6-luna` explicitly with reasoning effort `max`.
- If a Luna child discovers a missing material decision, stop and report
  `NEEDS_DECISION`. Do not invent the decision or silently reroute. The parent may
  reassess the task shape and explicitly reroute to the standard judgment lane
  (Terra/high) when that is appropriate; there is no automatic Luna-to-Terra fallback.
- `max` is a quality-first setting that must be evaluated on representative work. Treat
  Luna as a lower-cost implementation strategy subject to evaluation; do not claim fewer
  tokens or Codex subscription quota savings without evidence.

## Standard judgment lane

Use standard judgment for judgment-heavy integration, debugging, compatibility, and
similar work that is broader than a decision-complete implementation packet but does not
require a concrete frontier review.

- Request `gpt-5.6-terra` explicitly with reasoning effort `high`.
- If the task expands into architecture, security, concurrency, conflict-resolution, or
  other high-risk judgment, stop and report the expansion. The parent may explicitly
  choose the frontier lane after reassessing the task shape; there is no automatic
  Terra-to-Sol fallback.
- Terra is the balanced intelligence/cost judgment route. This is a routing heuristic,
  not a guarantee of quality, latency, token use, or quota consumption.

The role guidance is directional: Luna is suited to cost-sensitive or high-volume
implementation, Terra to intelligence/cost balance, and Sol to frontier judgment. These
roles do not establish task correctness or guarantee a particular cost or quota outcome.

The v1 diagnostic scripts retain historical capability labels for compatibility with
existing records. Those labels do not authorize explicit model routing for a new task.

## Frontier lane

Use the frontier lane only when a concrete architecture, security, concurrency,
conflict-resolution, or similarly difficult review need is written into the parent
packet.

- Request `gpt-5.6-sol` explicitly with reasoning effort `high` for a concrete frontier
  need.
- `xhigh` is allowed only when the parent records why `high` is insufficient for that
  concrete need; it is not a default.
- A required Sol route that is unavailable is `NOT_VERIFIED`. Do not downgrade it to a
  different model or silently replace it with a parent self-review.
- A frontier child is still a reviewer or work packet, not an independent acceptance
  authority. The parent reruns checks and accepts the result.

## Evidence contract

Keep requested and resolved model values separate. A requested model comes from the
parent spawn call. A resolved model comes only from the host's allowlisted runtime
metadata. Without that metadata, report the evidence gap and do not claim a model. A
successful runtime routing observation is not evidence that the task result is correct.
