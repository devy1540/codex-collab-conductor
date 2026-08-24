# Routing

Choose execution shape and assurance independently.

## Execution route

### solo

Use when the task is small, tightly coupled, or cheaper to complete directly than to explain and integrate.

Typical signals:

- One localized edit or answer.
- One root cause and one code path.
- Shared state makes parallel work unsafe.
- Delegation would repeat the primary agent's required reading.

### parallel-read

Use when at least two questions can be answered without sharing mutable state.

Good lanes include:

- Repository path or ownership mapping.
- Independent failure clusters.
- Documentation versus local implementation.
- Security, test, and maintainability review of the same read-only diff.

Run as many lanes as are genuinely independent and supported by current capacity. Batch the remainder when capacity is lower than demand.

Execution contract:

1. Build one self-contained read-only packet per lane.
2. Spawn every lane before starting primary-thread investigation.
3. Confirm a non-empty child ID for each accepted lane.
4. Wait for the confirmed children.
5. If spawning fails, do not replace the missing lane with an empty wait or claim parallel execution.

### delegated-build

Use one writer when the objective, owned files, interfaces, constraints, and verification are complete enough that the child should not invent product or architecture decisions.

Do not delegate implementation when:

- Material requirements remain unresolved.
- File ownership cannot be bounded.
- The change requires frequent decisions across shared modules.
- The primary agent would need to redo the implementation to verify it.

### plan-run

Use for an approved plan with multiple implementation slices. Dispatch a fresh implementer per slice, normally sequentially. Parallelize slices only when ownership and interfaces are disjoint and stable.

For long runs or likely compaction, keep a concise task ledger only when the repository has an approved local scratch convention. Otherwise use the available plan or goal state without creating new repository artifacts.

## Assurance route

### parent-check

Default for ordinary work. The primary agent owns diff inspection and verification.

### independent-review

Use for material regression risk, public contracts, authentication, authorization, payments, data integrity, migrations, concurrency, infrastructure, or an explicit independent-review request.

### dual-review

Use only when both implementation correctness and architectural boundaries require independent scrutiny. Run one code-quality/security lane and one architecture/devil's-advocate lane on the same verified diff.

## Route escalation

Escalate when new evidence reveals wider blast radius, hidden coupling, security sensitivity, or an incorrect initial specification. Do not silently downgrade an assurance level after work starts.
