---
name: codex-collab-conductor
description: Automatically coordinate Codex native subagents for coding, debugging, research, review, and multi-step repository work when independent lanes, bounded delegation, or fresh verification can materially improve speed or correctness. Apply without requiring explicit invocation when the host permits implicit skill selection. Skip trivial one-step edits, tightly coupled work, and tasks where delegation would add more coordination than value.
---

# Codex Collaboration Conductor

Use Codex native subagents as a proportional execution and assurance layer. Keep the primary agent responsible for intent, scope, integration, and final verification.

## Route before delegating

Default to direct execution. Select the smallest useful route:

- solo: one agent can finish and verify the task directly.
- parallel-read: two or more independent read-only questions can be investigated concurrently.
- delegated-build: a complete, bounded implementation packet can be owned by one child.
- plan-run: an approved multi-task plan has mostly independent implementation slices.

Select assurance separately:

- parent-check: the primary agent inspects the complete diff and reruns relevant checks.
- independent-review: a fresh child reviews the verified diff without implementation context.
- dual-review: fresh code and architecture review lanes run concurrently for broad or high-risk changes.

Read references/routing.md when the route is not obvious or the task is broad, risky, or multi-step.

## Delegate with clean context

- Prefer fork_turns set to none so the child receives only its task packet.
- Use the task packet contract in references/task-packets.md.
- For every non-solo route, the delegation gate is mandatory: call collaboration.spawn_agent or the exposed native spawn equivalent once per selected lane before any task-specific file read, shell command, browser action, or primary-thread investigation.
- Issue independent spawn calls together so they can run concurrently.
- Record the returned child thread IDs. Do not call wait with an empty target list.
- Wait only on children that were actually spawned. If no child ID was returned, delegation did not happen: report the native lane as unavailable and either use an explicitly allowed direct fallback or stop the required lane.
- Do not describe work as parallel, delegated, independent, or fresh-context unless the corresponding child thread was successfully created.
- Never simulate a child lane by doing its assigned investigation in the primary thread. A direct fallback is a declared route change, not successful delegation.
- Do not use delegation to avoid understanding the task or reading critical code.
- Do not ask children to recursively orchestrate. They report blockers, conflicts, scope expansion, and recommended handoffs upward.
- Do not make the primary agent duplicate work assigned to an active child.
- Track every non-solo lane using references/fallback-states.md and retain one lane receipt with immutable spawn-attempt history.

## Use proportional concurrency

- Parallelize independent read-heavy work first.
- Choose child count from the number of genuinely independent lanes and the runtime's available capacity. Do not target a fixed count.
- Use one writer at a time by default.
- Allow parallel writers only when file ownership is disjoint, interfaces are already fixed, and the primary agent can prove that the edits will not overlap.
- If ownership is uncertain, investigate first and write sequentially.

## Route models by capability

Read references/model-lanes.md before spawning children. Use explicit model and reasoning settings when the native spawn surface supports them.

- Fast exploration: GPT-5.3-Codex-Spark with low effort when the host exposes it; otherwise Luna with low effort.
- Bounded, fully specified implementation: Luna with max effort when available.
- Judgment-heavy implementation, integration, or debugging: Terra with high effort when available.
- Architecture, security, conflict resolution, and fresh final review: Sol with high or xhigh effort when available.

If a requested model or effort is unavailable, do not claim it was used. The only automatic cross-model fallback is Spark/low to Luna/low after an explicit model_unavailable failure. Other lanes require an evidence-backed declared reroute. A required independent frontier review remains unavailable rather than silently passing.

Prefer an explicit Spark model and low reasoning on each fast-lane spawn. Confirm the child's resolved model from runtime metadata before claiming Spark. If the host reports model_unavailable for explicit Spark routing, fall back to explicit Luna/low rather than changing the global subagent default silently.

When local Codex rollout files are available, use scripts/inspect_child_runtime.py with the exact child thread ID to obtain allowlisted routing evidence. Never inspect or expose transcript content merely to prove model identity.

Before accepting completed non-solo work, validate each lane receipt with scripts/validate_lane_receipt.py and the complete route with scripts/validate_route_manifest.py when local script execution is available.

## Verify and accept

- Treat child reports as claims, not proof.
- Wait for every requested lane before synthesis.
- Inspect the complete repository diff and changed-file scope.
- Rerun the smallest checks that directly prove the acceptance criteria, then broader checks when the claim requires them.
- Reconcile conflicting child findings explicitly.
- Accept a non-solo route only when every required lane's final state is SUCCEEDED and its final valid attempt has routing evidence. Earlier failed attempts remain history and do not invalidate a successful permitted fallback. A required frontier review failure leaves the deliverable NOT_VERIFIED.
- For behaviorally read-only reviewers, capture repository state before and after review; any mutation invalidates that review.
- Follow references/assurance.md for high-risk review gates and correction loops.

## Delegation invariant

For a non-solo route, the first task-execution tools after loading the required skill references must be native spawn calls. If that invariant is violated, stop claiming the non-solo route, declare the route failure, and reassess before continuing.

## Stop conditions

Stop when the requested outcome is verified, the user stops the task, a destructive or external action needs new authority, or a precise blocker leaves no safe in-scope path. Do not keep spawning agents after additional lanes stop improving the evidence.

## Design sources

This original workflow is inspired by publicly documented ideas from oh-my-codex, Sol Advisor, and Superpowers. It uses Codex native subagents rather than copying or requiring those projects' external runtimes.
