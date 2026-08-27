---
name: review-pr
description: "Evidence-first multi-agent review of GitHub PRs, branch diffs, and local working-tree changes. Use for code review that must inspect repository context, route auth/data/API/infra/UI risks to specialist reviewers, challenge false positives, separate code/CI/deployment evidence, and return file:line findings without posting or modifying anything."
---

# Review PR

## Overview

This skill is only for code review. It materializes a PR, branch diff, or local working tree into local artifacts with `scripts/prepare_review.py`, then uses Codex sub-agents to separate recon, specialist review, challenge, and synthesis.

Do not turn this into a general PR automation flow. The goal is a review report, not comment posting, pipeline state, or repo maintenance.

## Model routing contract

Before the first sub-agent spawn, read `references/model-routing.json`. It is the sole
model and reasoning-effort policy for review roles. Every reviewer spawn must set both
`model` and `reasoning_effort` from the matching route. Never rely on parent model inheritance.

Preserve the parent model and effort. The parent still owns scope, integration, acceptance,
and the final response. Use the `frontier` route only when recon or the challenge pass proves
one of its concrete `required_triggers`; ordinary quality, security, specialist, challenge,
and synthesis work stays on its named standard route. If a required route is unavailable,
stop that lane and report `NOT_VERIFIED`; do not silently inherit the parent or switch models.

The ordinary workflow spawn roles are exactly `workflow_roles` in the contract. Before a
`frontier` spawn, build a `frontier_evidence` object containing the matched trigger ID,
the standard-review findings with severity/category/file/line, and the challenge state.
Include conflicting reviewer conclusions when that trigger requires them. Do not spawn
`frontier` without a complete evidence object that satisfies every field of one trigger,
and never spawn more than `max_spawns_per_review`.

## Workflow

### 1. Lock scope and read repository instructions

Restate the exact PR, branch/base pair, or working tree being reviewed. Respect user boundaries such as review-only, no comments, no fixes, or one named module.

Before evaluating the patch, read applicable repository instructions and the smallest set of product or architecture documents needed to understand the contract. Do not invent requirements from file names or screenshots. When a PR claims to implement a specification, inspect that specification directly.

### 2. Materialize the review target

Resolve the absolute directory containing this loaded `SKILL.md` as
`REVIEW_PR_SKILL_ROOT`. Never assume the standalone `~/.codex/skills` path because this
skill may be installed from a plugin cache. Run exactly one of these commands from the
repository you want to review, replacing the example root with the resolved path:

```bash
REVIEW_PR_SKILL_ROOT="/absolute/path/to/loaded/review-pr"
python3 "$REVIEW_PR_SKILL_ROOT/scripts/prepare_review.py" --pr 123
python3 "$REVIEW_PR_SKILL_ROOT/scripts/prepare_review.py" --pr 123 --repo owner/repo
python3 "$REVIEW_PR_SKILL_ROOT/scripts/prepare_review.py" --branch feature/refactor-auth --base main
python3 "$REVIEW_PR_SKILL_ROOT/scripts/prepare_review.py" --base main
python3 "$REVIEW_PR_SKILL_ROOT/scripts/prepare_review.py" --working-tree
```

The script writes artifacts under `.git/codex-review-pr/...` when inside a git worktree, so the review does not dirty the tracked worktree.

After the script runs, read at least:
- `summary.md`
- `meta.json`
- `changed-files.txt`
- `diff-stat.txt`
- `diff.patch`
- `untracked-files.txt` when present

Stop when `empty_diff` is true. If `diff.patch` is empty but working-tree metadata lists untracked files, inspect only the relevant untracked files directly and preserve that blind-spot disclosure.

In working-tree mode, `diff.patch` includes staged and unstaged tracked changes. Untracked paths are inventoried but their contents are not copied into the patch. Recon must inspect relevant untracked files directly and report that boundary.

For PR mode, `meta.json` also captures the exact base/head SHAs and current CI/review metadata. CI state is context, not proof that changed code is correct.

### 3. Run recon and risk routing first

Spawn one read-only sub-agent for factual codebase mapping before any evaluative review.
Use the `recon` route from `references/model-routing.json` and pass its model and effort
explicitly in the spawn call.

Give the recon agent:
- the artifact paths from Step 2
- the repository root
- the prompt scaffold in `references/reviewer-roles.md`

Recon must produce:
- changed modules and entry points
- dependency edges and affected tests
- hidden blast radius
- risky files or follow-up files that are not in the patch but matter for review
- applicable repository instructions and claimed requirements
- a risk profile using `references/risk-routing.md`

Keep recon concise. Downstream reviewers should inherit the recon summary, not the full exploratory transcript.

### 4. Run quality, security, and selected specialist reviews

Spawn quality and security reviewers in parallel after recon for every non-trivial review. Then add only the specialists triggered by concrete patch evidence:

- contract/compatibility
- data/migration
- operations/release
- UI/product-contract

Run additional specialists in bounded batches. Do not spawn a specialist merely because its category sounds generally useful.
Use the corresponding `quality`, `security`, or specialist route from
`references/model-routing.json` for every spawn. Add a separate `frontier` reviewer only
when a matched trigger ID and complete `frontier_evidence` are available; attach that
evidence to the frontier prompt. Do not upgrade the default security reviewer merely
because the patch touches authentication or sensitive code.

Give each reviewer:
- artifact paths
- recon summary
- applicable requirements and risk profile

Require a normalized finding schema:
- severity
- confidence
- file
- line
- title
- issue
- impact
- recommendation

Security findings should also include CWE and OWASP category when applicable.

Every reviewer must distinguish:

- issue proven by the patch and surrounding code
- missing evidence or test coverage
- runtime or deployment concern that code review alone cannot verify

Instruct both reviewers to ignore:
- style-only nits
- generic maintainability complaints without evidence
- speculative vulnerabilities without concrete proof

If one reviewer finishes materially earlier, you may relay the other reviewer's top findings with `send_message` and ask for a short addendum. Do not block the pipeline on cross-consultation.

### 5. Run the challenge pass

Spawn a challenge agent after aggregating quality, security, and selected specialist findings.
Use the `challenge` route from `references/model-routing.json`. If the challenge output
proves a frontier trigger, record the matched trigger ID and complete `frontier_evidence`
before spawning one fresh `frontier` reviewer, then re-run challenge after reconciling
that result. Without complete evidence, keep the standard verdict and record the gap.

Give it:
- the reviewer outputs
- the recon summary
- `references/review-standards.md`

The challenge pass should:
- mark findings as `keep`, `weaken`, or `discard`
- identify duplicate concerns
- name missing context, framework protections, or mitigating evidence
- list blocking questions that still need resolution
- reject findings based only on stale remote state, mutable tags, screenshots, or unspecified product expectations

### 6. Check validation evidence

Inspect targeted tests, CI checks, schema or generated artifacts, and relevant build commands in proportion to the risk. Do not imply a command was executed unless its output was observed in this review.

Keep these proof layers separate:

- code and diff inspection
- local test/build result
- CI result for an exact SHA
- artifact or image identity
- Argo CD/Kubernetes rollout
- runtime behavior

A merged PR is not deployment proof. When deployment verification is requested, hand that portion to `$deploy-check` rather than expanding this skill into a release workflow.

### 7. Synthesize the verdict

Spawn a synthesis agent with recon, review, and challenge outputs.
Use the `synthesis` route from `references/model-routing.json` explicitly; synthesis must
not inherit the parent model.

Require the synthesis agent to produce:
- a final verdict: `approve`, `comment`, or `request_changes`
- deduped findings ordered by severity then confidence
- discarded or weakened findings
- blind spots
- validation evidence and unverified proof layers
- concise rationale

When the user asked for a review, findings must appear first in the final answer. Keep the summary brief and secondary to the findings.

## Execution Notes

- Prefer the GitHub plugin for PR metadata when available, and use `gh` for diff acquisition either way.
- Prefer `rg` for targeted code discovery after recon identifies hotspots.
- Keep all reviewer agents read-only. Do not ask them to edit files or post comments.
- Treat the multi-agent structure as mandatory for non-trivial reviews. Do not collapse recon, challenge, and synthesis into one agent unless the diff is empty or trivially small.
- Preserve the user's requested scope. Review-only does not authorize fixes, comments, commits, pushes, or issue creation.
- Recheck current refs before relying on ahead/behind or branch state. Do not treat a previous task's repository snapshot as current evidence.
- Keep shared state in memory unless prompts become too large. If you need intermediate files, place them next to the prepared artifacts and use `recon.md`, `quality.md`, `security.md`, `challenge.md`, and `verdict.md`.
- Do not claim an issue without `file:line` evidence or an equally concrete source.
- Do not use vague hedges. Apply `references/review-standards.md` before returning the verdict.

## Non-goals

- Do not post GitHub review comments unless the user explicitly asks.
- Do not expand scope from the requested PR or diff to the whole repository unless recon proves the patch is impossible to understand otherwise.
- Do not add planning, issue triage, CI fixing, or implementation work to the review flow.
- Do not claim that a merge, image, rollout, migration, feature flag, or user flow is live from source review alone.

## Resources

- `references/reviewer-roles.md`: role prompts and expected outputs for recon, quality, security, challenge, and synthesis
- `references/review-standards.md`: evidence rules, severity and confidence calibration, challenge heuristics, and final report shape
- `references/risk-routing.md`: evidence-based specialist selection
- `references/model-routing.json`: explicit model and reasoning-effort contract for every review role
- `scripts/prepare_review.py`: deterministic target resolution and artifact materialization
