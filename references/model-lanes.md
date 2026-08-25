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
  unavailable or the host reports a pre-child quota denial, make one retry with
  `gpt-5.6-luna` and reasoning effort `low` explicitly.
- Do not switch models after a Spark child has started and then times out or reports a
  child error. Report the lane failure or change the task route explicitly; do not call
  that event a fast fallback.
- Do not change a global default to obtain Spark. Route this lane per spawn call.

The pre-child fallback is a resilience rule, not a speed or quality claim. If the host
reports a quota condition that cannot be represented by the existing v1 diagnostic
causes, omit the optional receipt instead of inventing a cause.

## Bounded and standard lanes

Bounded implementation and standard judgment lanes use the Codex host default. Do not
send a concrete model ID or reasoning setting for these lanes, and do not claim that the
host selected a particular named model. If the host exposes a resolved model in runtime
metadata, it may be recorded as observed evidence only; absence of that evidence is not
a reason to infer it.

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
