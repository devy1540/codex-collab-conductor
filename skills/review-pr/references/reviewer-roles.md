# Reviewer Roles

Use these prompts as starting points. Keep every sub-agent read-only and ask for final findings only.

## Recon

Use an `explorer` agent when the task is primarily codebase mapping.

Goal:
- Read `summary.md`, `meta.json`, `diff.patch`, and the most relevant surrounding files.
- Map changed files to modules, entry points, dependencies, and tests.
- Identify hidden blast radius outside the patch.
- Read applicable repository instructions and named product requirements.
- Produce an evidence-based risk profile for specialist routing.

Required output:

```md
## Recon
- Target: PR #123 / branch diff
- Changed modules: ...
- Entry points and dependencies: `path:line`, `path:line`
- Follow-up files to inspect: `path:line`
- Risk hotspots: ...
- Applicable instructions/requirements: `path:line`
- Risk profile: auth/data/contract/operations/UI plus trigger evidence
- Blind spots or unanswered context: ...
```

Rules:
- Report facts first and cite files.
- Do not assign severity.
- Keep the result concise enough to paste into downstream reviewer prompts.
- Do not convert a filename, screenshot, or PR description into a requirement without checking its source.

## Quality

Goal:
- Find bugs, regressions, invariant violations, error-handling gaps, missing tests, and maintainability issues that are likely to cause real defects.

Focus:
- state transitions
- boundary conditions
- nullability and error paths
- concurrency or ordering assumptions
- migration safety
- tests missing for risky changes

Output every finding in this shape:

```md
## Findings
1. [high][0.91] Missing rollback on partial update
   - File: `src/orders/service.ts:184`
   - Issue: ...
   - Impact: ...
   - Recommendation: ...
   - Evidence: `src/orders/service.ts:184`, `src/orders/repo.ts:52`
```

Rules:
- Ignore style-only feedback.
- Do not invent impact without traceable evidence.
- Use `low` or `info` only when the issue is real but non-blocking.

## Security

Goal:
- Find concrete security issues in the changed code only.

Focus:
- authorization and authentication
- injection
- secrets
- unsafe deserialization
- SSRF and outbound trust
- crypto or token misuse
- logging of sensitive data

Output every finding in this shape:

```md
## Findings
1. [high][0.89] Authorization check missing on admin mutation
   - File: `src/api/admin.ts:73`
   - Security: CWE-862 | OWASP A01
   - Issue: ...
   - Impact: ...
   - Recommendation: ...
   - Evidence: `src/api/admin.ts:73`, `src/auth/policy.ts:14`
```

Rules:
- Do not report hypothetical vulnerabilities without proof.
- Name framework protections when they invalidate a suspected issue.

## Contract And Compatibility

Use only when the patch changes an API, event, schema, shared type, SDK, public function, authentication boundary, or cross-repository contract.

Focus:
- producer/consumer compatibility
- rollout ordering and mixed-version behavior
- request/response, event, cookie, token, and feature-flag contracts
- generated clients, migrations, fixtures, and documentation that must change together

Require evidence from both sides of the contract when available. A changed producer alone is not proof that consumers remain compatible.

## Data And Migration

Use only when the patch changes persistence, migrations, queues, reconciliation, transactions, backfills, encryption, or deletion behavior.

Focus:
- forward and rollback compatibility
- partial failure and retry behavior
- idempotency and duplicate processing
- old/new row compatibility
- data-loss and irreversible-transition boundaries

Do not run write queries or apply migrations during review. Treat a checked-in migration as code evidence, not proof it ran anywhere.

## Operations And Release

Use only when the patch changes Dockerfiles, CI, manifests, Helm/Kustomize, runtime flags, health checks, image builds, or architecture-specific binaries.

Focus:
- artifact identity and architecture
- configuration defaults and missing secrets
- probes, rollout strategy, rollback, and mixed-version safety
- whether validation actually covers the built/deployed artifact

Do not claim the change is deployed. State the exact source-level operational risk and hand live verification to `deploy-check` when requested.

## UI And Product Contract

Use only when a design, specification, prototype, or established UI contract is available.

Focus:
- required copy, states, navigation, accessibility, layout, and interaction behavior
- wrapper DOM or platform behavior that invalidates visual assumptions
- loading, empty, error, permission, and recovery states
- whether automated checks cover the actual contract

Do not invent visual requirements. If a reported mismatch is found, re-check the whole applicable contract instead of only the reported element.

## Challenge

Goal:
- Attack the weakest findings before they reach the final verdict.

For each incoming finding, decide:
- `keep`
- `weaken`
- `discard`

Check:
- evidence quality
- hidden assumptions
- framework protections
- contradictory code context
- duplicate root causes
- severity inflation
- requirement source and proof-layer confusion
- stale branch, CI, image, or deployment evidence

Required output:

```md
## Challenge
1. keep
   - Target: finding 2
   - Reason: ...
2. weaken
   - Target: finding 4
   - Reason: severity should drop from high to medium because ...
3. discard
   - Target: finding 5
   - Reason: middleware already enforces the check at `src/http/router.ts:41`

## Blocking Questions
- ...
```

## Synthesis

Goal:
- Deduplicate findings, retain the strongest evidence, calibrate confidence, and render the final verdict.

Verdict guidance:
- `approve`: no high-severity blockers remain
- `comment`: only non-blocking medium or low findings remain
- `request_changes`: at least one high-severity blocker remains, or multiple medium issues combine into release risk

Required output:

```md
## Verdict
- request_changes

## Findings
1. [high][0.93] ...
   - File: `path:line`
   - Found by: quality, security
   - Impact: ...
   - Recommendation: ...

## Discarded Or Weakened Findings
- ...

## Blind Spots
- ...

## Validation Evidence
- Code/diff inspected: ...
- Tests/build observed: ...
- CI observed for exact SHA: ...
- Deployment/runtime: verified / not requested / unverified
```

Rules:
- Preserve reviewer attribution.
- Merge only true duplicates, not merely similar symptoms.
- Keep the rationale short and evidence-backed.
- Never translate a code-review verdict into a deployment or runtime verdict.
