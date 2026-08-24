# Model lanes

Use capability classes so model generations can change without rewriting role prompts.

The concrete model IDs below are current example defaults, not universal requirements. Verify that the selected Codex host and account expose them. Preserve the capability class and choose an available equivalent when a noncritical lane permits fallback.

## Fast lane

Default:

- Model: gpt-5.6-luna
- Reasoning effort: low

Use for repository search, symbol mapping, log classification, large-input triage, formatting review, and other bounded read-heavy work.

## Bounded implementation lane

Default:

- Model: gpt-5.6-luna
- Reasoning effort: max

Use only when the task packet fully specifies objective, file ownership, interfaces, constraints, and verification. The higher effort is intended to execute a strong specification, not to resolve missing product or architecture decisions.

If the child discovers missing decisions, it should stop the implementation slice and report the ambiguity upward. Correct a specification error once when appropriate; otherwise reroute judgment-heavy work to Terra.

## Standard judgment lane

Default:

- Model: gpt-5.6-terra
- Reasoning effort: high

Use for multi-file integration, debugging, pattern-sensitive implementation, test strategy, compatibility review, and work with meaningful but bounded judgment.

## Frontier lane

Default:

- Model: gpt-5.6-sol
- Reasoning effort: high

Use xhigh only for architecture, subtle security or concurrency analysis, difficult conflict resolution, or other cases where deeper reasoning has a concrete quality benefit.

Use the frontier lane for fresh final review when independent review is a required acceptance gate.

## Routing evidence and fallback

- Pass model and reasoning explicitly when supported.
- Prefer a fresh context for every independent review and each unrelated implementation slice.
- If the runtime omits model evidence, report the selected role and the evidence gap rather than asserting a model identity.
- Fast and standard lanes may inherit the parent after an unavailable-model failure when the cost or behavior change is disclosed.
- A required frontier review does not pass through silent fallback.
