# Lane states and fallback

Separate one spawn attempt, one logical lane, and the overall route.

## Attempt states

- SPAWNING: a native spawn request is in flight.
- RUNNING: a non-empty child ID was returned.
- SUCCEEDED: the child result and required routing evidence were received.
- FAILED: the attempt cannot satisfy its contract.

Attempt states are immutable after SUCCEEDED or FAILED. A fallback creates a new attempt and preserves the failed attempt as history.

## Lane states

- PENDING: the task packet is complete but no attempt is active.
- RUNNING: the lane has one active attempt.
- SUCCEEDED: the lane has a final valid SUCCEEDED attempt.
- FAILED: no permitted attempt can satisfy the lane.

## Route state predicates

Evaluate these in order so exactly one route state applies:

1. RUNNING: at least one required lane is PENDING or RUNNING.
2. SUCCEEDED: all required lanes are SUCCEEDED.
3. FAILED: all required lanes are FAILED.
4. PARTIAL: required lanes contain both SUCCEEDED and FAILED.

A non-solo route must have at least one required lane.

## Causes

Use one attempt cause:

- none
- capacity
- model_unavailable
- timeout
- child_error
- evidence_missing

Keep verification outcome separate:

- VERIFIED
- NOT_VERIFIED

## Transitions

- Lane PENDING -> attempt SPAWNING immediately before the native spawn call.
- Attempt SPAWNING -> RUNNING only after a non-empty child ID is returned.
- Attempt RUNNING -> SUCCEEDED after the result and routing evidence arrive.
- Attempt SPAWNING or RUNNING -> FAILED when that attempt cannot complete.
- Lane -> SUCCEEDED when its final valid attempt is SUCCEEDED.
- Lane -> FAILED when no permitted attempt remains.

Never wait on a lane without an active attempt and non-empty child ID.

## Fallback matrix

### Fast lane

Request Spark/low explicitly. Only an explicit model_unavailable failure permits one automatic cross-model retry. Create one new Luna/low attempt, set fallback_used to spark_to_luna, and retry at most once.

Do not switch models automatically for capacity, timeout, or child_error.

### Capacity

Capacity is not a model failure. Keep unstarted lanes PENDING, wait for active child IDs, then start the next bounded batch. Do not create a failed attempt merely because no slot was available. If capacity is still unavailable after one completed batch releases its slots, fail the lane with cause capacity.

### Standard and implementation lanes

Do not inherit the parent model or silently change capability class. A Luna-to-Terra reroute requires evidence that the task needs more judgment, closes the old route, and creates a new route with a standard lane. The new route records supersedes_route_id for the old route and names the failed bounded lane in replaces_lane. Every other required lane from the old route keeps its capability, remains required, and must be re-proved by a fresh child in the new route.

### Required frontier review

A required Sol review has no lower-capability fallback. Preserve the actual failure cause, set the lane FAILED, and set the deliverable verification outcome to NOT_VERIFIED.

## Lane receipt

Record one lane receipt with attempt history:

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

The validator binds every successful attempt to a completed child turn and checks parent_thread_id, model, and reasoning effort. Post-spawn failed attempts must bind their exact child ID and turn ID to the requested model and effort, even when no task_complete event exists. A claimed child ID without matching rollout evidence is invalid.

The primary agent may report a non-solo route complete only when each required lane in the current route has final state SUCCEEDED and its final valid attempt has routing evidence. Earlier failed attempts remain valid history and do not block a successful permitted fallback.

Validate a completed receipt with scripts/validate_lane_receipt.py before using it as an acceptance gate.

## Route manifest

Record the complete route separately from lane receipts:

    schema_version: ccc-route-manifest-v1
    route_id: <route UUID>
    supersedes_route_id: <prior route UUID or null>
    replaces_lane: <failed bounded lane name or null>
    parent_thread_id: <parent thread UUID>
    state: SUCCEEDED | PARTIAL | FAILED
    required_lanes: [<lane names>]
    lanes: [<complete lane receipts>]

Validate all lane receipts together with scripts/validate_route_manifest.py. The route manifest enforces one parent and route ID, unique lanes, unique child ownership across lanes, required-lane membership, derived route state, and auditable reroute linkage. A reroute may replace exactly the named failed bounded lane; it cannot drop or downgrade other required lanes or reuse child evidence from the superseded route.
