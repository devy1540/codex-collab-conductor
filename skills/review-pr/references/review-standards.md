# Review Standards

## Evidence Rule

Every reported finding needs concrete evidence. Acceptable evidence includes:
- `file:line`
- test result names
- metrics
- authoritative external references when the code alone is insufficient

If a claim has no evidence, discard it.

Separate evidence by proof layer:

1. source and surrounding code
2. local test or build output observed in this review
3. CI result tied to an exact commit SHA
4. built artifact or image digest
5. deployed workload and runtime behavior

Evidence at one layer must not be presented as proof of a later layer.

## Language Rule

Avoid vague hedges such as:
- `it depends`
- `generally`
- `might`
- `could potentially`
- `in some cases`
- `arguably`
- `it seems`

State the condition, probability, or proof instead.

## Severity

Use this scale:
- `high`: directly evidenced functional breakage, security exposure, data corruption, privilege failure, irreversible migration risk, or release blocker
- `medium`: directly evidenced defect, compatibility gap, migration risk, or missing protection with meaningful blast radius
- `low`: real but non-blocking issue with limited blast radius
- `info`: noteworthy context that should not drive the verdict on its own

## Confidence

Use a `0.00-1.00` confidence score.

Calibration guide:
- `0.90-1.00`: directly evidenced by code path, invariant, or known exploit pattern
- `0.75-0.89`: strong evidence, minor assumptions remain
- `0.50-0.74`: plausible but incomplete; challenge pass should usually weaken or discard unless more evidence appears
- `<0.50`: do not surface in the final findings

## Challenge Heuristics

The challenge pass should search for:
- hasty generalization from one code snippet to a system-wide claim
- false dilemma between rewrite and acceptance
- survivorship bias from happy-path-only reasoning
- correlation mistaken for causation
- hidden framework or middleware protections
- duplicate findings with one underlying root cause
- an unstated product requirement being treated as fact
- CI, merge, image tag, screenshot, or rollout state being used at the wrong proof layer

## Scope Rule

Review the requested diff, not the whole repository.

Respect explicit user limits such as review-only, one PR, no fixes, no comments, or one module. A review request does not authorize editing, posting, committing, pushing, or deploying.

You may inspect surrounding code only to answer one of these questions:
- what invariant the changed code depends on
- whether a claimed issue is already mitigated
- which caller or callee makes the diff risky

## Final Report Shape

When the user asked for a review:
1. List findings first, ordered by severity then confidence.
2. List open questions or assumptions second.
3. Keep the summary brief and secondary.

Every surviving finding should include:
- severity
- confidence
- title
- `file:line`
- issue
- impact
- recommendation
- reviewer attribution in the synthesized report

After findings, include:

- exact target and SHAs
- validation commands actually observed
- CI state tied to the reviewed SHA when available
- blind spots, including untracked content not copied into the patch
- explicit deployment/runtime verification status
