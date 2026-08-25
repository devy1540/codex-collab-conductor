# Optional diagnostic states and fallback history

This reference describes the existing v1 diagnostic format. Receipts and route manifests
are optional runtime diagnostics, not required workflow artifacts. They help bind a
high-risk routing observation or troubleshoot a fallback; they never establish that a
child produced a correct task result. Receipt v2 and manifest v2 are outside the current
workflow; do not invent unsupported host evidence to create them.

## Attempt states

- `SPAWNING`: a native spawn request is in flight.
- `RUNNING`: a non-empty child ID was returned.
- `SUCCEEDED`: the child result and requested routing evidence were received.
- `FAILED`: the attempt cannot satisfy its contract.

Attempt states are immutable after `SUCCEEDED` or `FAILED`. A permitted fallback creates
a new attempt and preserves the failed attempt as history.

## Lane states

- `PENDING`: the packet is complete but no attempt is active.
- `RUNNING`: the lane has one active attempt.
- `SUCCEEDED`: the lane has a final valid successful attempt.
- `FAILED`: no permitted attempt can satisfy the lane.

## Route state predicates

Evaluate these in order so exactly one route state applies:

1. `RUNNING`: at least one required lane is `PENDING` or `RUNNING`.
2. `SUCCEEDED`: all required lanes are `SUCCEEDED`.
3. `FAILED`: all required lanes are `FAILED`.
4. `PARTIAL`: required lanes contain both `SUCCEEDED` and `FAILED`.

A non-solo route must have at least one required lane. Never wait on a lane without an
active attempt and a non-empty child ID.

## Causes and verification

The existing v1 cause values are:

- `none`
- `capacity`
- `model_unavailable`
- `timeout`
- `child_error`
- `evidence_missing`

Keep verification separate from attempt state:

- `VERIFIED`: only the allowlisted runtime routing evidence matched the diagnostic.
- `NOT_VERIFIED`: the routing evidence or required route could not be established.

Neither value is a task-result verdict. The parent must use the diff, tests, and relevant
runtime behavior to decide whether the task itself is correct.

## Fallback boundary

The only automatic cross-model fallback is the fast-lane pre-child unavailable/quota
retry defined in `model-lanes.md`, and it is permitted at most once. A started fast child
that times out or reports `child_error` does not trigger a model switch. Frontier Sol
unavailability has no downgrade and remains `NOT_VERIFIED`. Bounded and standard lanes
use the host default; any reroute must be declared as a route decision, not hidden in a
receipt.

If a host exposes quota as a cause that the existing v1 validator cannot represent, omit
the optional receipt rather than fabricating `model_unavailable` or another value.

## v1 lane receipt

When a parent explicitly chooses to record a diagnostic, use the existing
`ccc-lane-receipt-v1` shape:

    schema_version: ccc-lane-receipt-v1
    route_id: <route UUID>
    supersedes_route_id: <prior route UUID or null>
    parent_thread_id: <parent thread UUID>
    lane: <name>
    capability: fast | bounded_implementation | standard | frontier
    required: true | false
    state: SUCCEEDED | FAILED
    verification: VERIFIED | NOT_VERIFIED
    fallback_used: none | spark_to_luna
    attempts:
      - number: <1-based integer>
        state: SUCCEEDED | FAILED
        cause: none | capacity | model_unavailable | timeout | child_error | evidence_missing
        child_id: <id or null>
        turn_id: <turn UUID or null>
        requested_model: <model>
        resolved_model: <observed model or null>
        reasoning_effort: <requested effort>

The existing validator binds successful attempts to a completed child turn and checks
parent, model, and effort evidence. It is compatibility tooling only. In particular,
historical capability labels in a v1 receipt do not authorize a new explicit route.

Validate a diagnostic only when it was intentionally recorded:

    python3 scripts/validate_lane_receipt.py /path/to/lane-receipt.json

## v1 route manifest

For a multi-lane diagnostic, use the existing `ccc-route-manifest-v1` shape:

    schema_version: ccc-route-manifest-v1
    route_id: <route UUID>
    supersedes_route_id: <prior route UUID or null>
    replaces_lane: <failed bounded lane name or null>
    parent_thread_id: <parent thread UUID>
    state: SUCCEEDED | PARTIAL | FAILED
    required_lanes: [<lane names>]
    lanes: [<complete lane receipts>]

The validator enforces one parent and route ID, unique lanes, unique child ownership,
required-lane membership, derived route state, and auditable reroute linkage. A reroute
must name the failed bounded lane in `replaces_lane`, retain every other required lane at
the same capability, and use fresh child evidence. These checks still do not prove task
correctness.

    python3 scripts/validate_route_manifest.py /path/to/route-manifest.json

## Acceptance boundary

The parent may complete an ordinary route without a receipt or manifest. For a high-risk
route, missing diagnostics means missing routing proof, not a reason to invent success.
Final acceptance remains parent-owned diff inspection and verification reruns. An
optional fresh review is a second opinion and must be re-verified after any correction.
