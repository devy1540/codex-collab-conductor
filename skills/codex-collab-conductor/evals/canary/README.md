# Manual native canary

This directory is a manual release-gate package for CCC. It contains only synthetic,
read-only fixtures and instructions. It does not start native children, simulate a
result, or claim that the policy is faster, more correct, or independently assuring.

Run exactly one functional execution for each of these six scenarios:

- `solo-guard`
- `parallel-read`
- `fast-route-fallback`
- `bounded-implementation`
- `standard-judgment`
- `frontier-seeded-defect-review`

Use `playbook.md` for the route decision and pass criteria. Record one redacted result
per scenario using `result-template.json` and validate it against `result-schema.json`.
The result may contain only the schema fields, including the fixture digest, child counts,
distinctness, unchanged-worktree check, requested/resolved model and effort, fallback/failure
class, routing verification, task `PASS`/`FAIL`, wall time, and parent rework. Never add
prompts, child IDs, local paths, or transcripts.

The canary is a functional observation, not a benchmark. Do not publish a performance
claim until there are at least five repeated comparisons against a solo baseline. A
single run per scenario is the only run requested by this package.

`results/2026-08-25-*.json` records the first observed functional run of this package.
Those files are routing/task observations tied to fixture digests, not a benchmark or a
general quality claim.
