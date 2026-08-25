# Native subagent task packets

Every child receives a self-contained packet. Remove sections that truly do not apply, but never omit scope, constraints, verification, or return requirements for a writer.

## Common packet

ROLE

State the child's single responsibility and whether it may edit files.

OBJECTIVE

Describe the concrete outcome, not a vague activity.

SCOPE AND OWNERSHIP

Name relevant files, modules, systems, or investigation boundaries. For writers, state owned files and forbidden areas.

CONTEXT AND EVIDENCE

Provide only confirmed facts, relevant symptoms, decisions, and source references. Do not copy the whole parent transcript.

INTERFACES

State contracts, callers, schemas, compatibility boundaries, and dependencies that must remain stable.

CONSTRAINTS

State safety, authorization, compatibility, style, and non-goal boundaries.

VERIFICATION

Provide acceptance criteria and commands or observable checks that prove them.

RETURN

Require a concise report containing findings or changes, evidence, verification results, assumptions, blockers, and recommended handoffs. The report is a work product for the parent, not an acceptance verdict.

Choose task shape and assurance before model routing. The child packet should not invent a
concrete model or claim a resolved model; follow `references/model-lanes.md` and let the
parent own that choice.

For non-solo work, the parent may attach an optional v1 lane receipt containing
route_id, nullable supersedes_route_id, parent_thread_id, the lane's final state,
verification outcome, fallback_used, and immutable attempt history with cause, child_id,
turn_id, requested_model, resolved_model, and reasoning_effort. Omit the receipt when
routing diagnostics are not needed. The child must not infer fields that only the parent
runtime can observe. A receipt marked `VERIFIED` proves routing evidence only, not task
correctness.

## Explorer

- Read-only.
- Find repo-local files, symbols, data flow, and ownership.
- Return absolute paths and explain relationships.
- Do not propose architecture or implement changes unless the packet explicitly asks for recommendations.

## Researcher

- Read-only.
- Verify external, version-sensitive behavior using authoritative sources.
- Return direct links and distinguish official facts, inference, and uncertainty.
- Do not inspect private external data without the appropriate authorized connector.

## Implementer

- Edit only owned files.
- Use existing patterns and make the smallest defensible change.
- Run targeted checks and review the diff.
- Stop and report when a material decision is missing or ownership would expand.

## Verifier

- Do not implement fixes.
- Convert each acceptance criterion into PASS, FAIL, or PARTIAL with direct evidence.
- Distinguish failed behavior from unavailable proof.

## Reviewer

- Behaviorally read-only unless an enforced read-only sandbox is observed.
- Review the verified accumulated diff rather than implementation summaries.
- Lead with concrete findings, severity, impact, file references, and a specific correction.
- Return SHIP, FIX_FIRST, or RETHINK.
