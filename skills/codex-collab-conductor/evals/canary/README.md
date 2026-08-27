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

Use `playbook.md` for the route decision and pass criteria. Record one redacted v2 result
per scenario using `result-template.json` and validate it against `result-schema.json`.
The result may contain only the schema fields, including the fixture digest, child counts,
distinctness, unchanged-worktree check, execution route, capability lane, assurance route,
and one routing observation per synthetic lane. Each lane observation separates the
primary request, final resolved model, fallback cause, final failure class, and routing
verification. This represents mixed Spark/Luna outcomes without child IDs. Never add
prompts, child IDs, local paths, or transcripts.

The default validator accepts any schema-valid, semantically consistent observation,
including an honest `FAIL`/`NOT_VERIFIED` result. Run it again with `--release-gate` to
require every scenario to satisfy the release criteria. This keeps result validity separate
from the release decision.

The canary is a functional observation, not a benchmark. Do not publish a performance
claim until there are at least five repeated comparisons against a solo baseline. A
single run per scenario is the only run requested by this package.

`fixtures/v1/` and `results/v1/2026-08-25-*.json` preserve the original v1 inputs and
observations unchanged as auditable history. The first v2 parallel candidate is preserved
under `fixtures/history/` and `results/failed/`; one fallback child returned a sum instead
of the requested count. The revised current fixture defines count as cardinality, not sum,
and `results/2026-08-27-r2-parallel-read.json` records its one fresh passing execution.
These files are routing/task observations tied to fixture digests, not a benchmark or a
general quality claim.
