# Codex Collaboration Conductor

Codex Collaboration Conductor (CCC) is a single Codex skill that automatically coordinates native subagents when delegation materially improves speed, correctness, or independent verification.

It keeps simple work simple and adds proportional orchestration only when the task shape justifies it.

## What it provides

- Direct execution for trivial or tightly coupled work.
- Parallel native subagents for genuinely independent read-heavy lanes.
- Bounded implementation delegation with explicit file ownership.
- Capability-based model lanes for fast, standard, and frontier work.
- Fresh independent review for high-risk changes.
- Parent-owned diff inspection, verification reruns, and final acceptance.
- Hard guards against empty waits, simulated delegation, recursive orchestration, and overlapping writers.

CCC does not require custom agent TOML files, MCP servers, tmux, a daemon, or an external orchestration runtime.

## One skill, supporting resources

This repository contains one actual skill:

- SKILL.md

The remaining files support that skill:

- agents/openai.yaml: Codex UI metadata and implicit invocation policy.
- references/routing.md: solo, parallel-read, delegated-build, and plan-run decisions.
- references/model-lanes.md: Luna, Terra, and Sol example defaults by capability.
- references/task-packets.md: self-contained native child briefs.
- references/assurance.md: parent verification and fresh-review gates.
- references/fallback-states.md: deterministic spawn, failure, and fallback receipts.
- scripts/inspect_child_runtime.py: allowlisted child model and reasoning evidence.
- scripts/validate_lane_receipt.py: deterministic completed-lane receipt validation.
- scripts/validate_route_manifest.py: route-level child independence and reroute validation.
- tests/: standard-library regression tests for runtime inspection and policy contracts.

## Requirements

- A current Codex host with native subagents enabled.
- A native spawn surface that can return child thread IDs.
- Access to the selected models when explicit model routing is used.

Model IDs in this repository are example defaults for current Codex environments. The skill requires the capability class, not one permanent model generation.

## Install

Clone directly into the personal Codex skills directory:

    git clone https://github.com/devy1540/codex-collab-conductor.git \
      "$HOME/.codex/skills/codex-collab-conductor"

Restart Codex if the skill does not appear immediately.

## Automatic use

agents/openai.yaml enables implicit invocation. Codex can select the skill when the request matches the SKILL.md description, so users do not need to type the skill name on every task.

For stronger personal routing, add a rule like this to the user-level AGENTS.md:

    # Native subagent collaboration
    - When coding, debugging, research, or review has at least two independent lanes,
      or when separating implementation from independent verification materially helps,
      read and apply the codex-collab-conductor skill without requiring explicit invocation.
    - Skip trivial one-step work and tightly coupled work.
    - If a non-solo route is selected, spawn real native children before task-specific
      investigation. Never claim delegation without child IDs and never call an empty wait.

The repository does not modify AGENTS.md automatically.

## Model lanes

- Fast exploration: GPT-5.3-Codex-Spark with low reasoning when available, then GPT-5.6 Luna/low fallback.
- Fully specified bounded implementation: GPT-5.6 Luna with max reasoning when available.
- Judgment-heavy implementation and debugging: GPT-5.6 Terra with high reasoning when available.
- Architecture, security, conflict resolution, and fresh final review: GPT-5.6 Sol with high or xhigh reasoning when available.

The only automatic cross-model fallback is Spark/low to Luna/low after an explicit model_unavailable failure. Other lanes require an evidence-backed declared reroute. A required independent frontier review must not silently pass through fallback.

### Spark routing

CCC prefers explicit per-call routing for the fast lane:

    model = "gpt-5.3-codex-spark"
    reasoning_effort = "low"

Confirm the child session metadata before claiming Spark was used. If the host reports model_unavailable for explicit Spark routing, retry that noncritical lane once with explicit GPT-5.6 Luna/low and disclose the fallback.

Avoid setting Spark as the global default subagent model unless all other workflows explicitly route their children. A global default can unintentionally send unrelated reviewers or implementers from other skills to Spark/low.

## Inspect child routing

When local Codex rollout files are available, inspect one exact child thread:

    python3 scripts/inspect_child_runtime.py <child-thread-id>

Use a non-default session root when needed:

    python3 scripts/inspect_child_runtime.py <child-thread-id> \
      --sessions-dir /absolute/path/to/sessions

The inspector emits only allowlisted thread and turn IDs, a completion flag, depth, a known CCC model ID, and a known reasoning effort. It never outputs agent paths, prompts, messages, tool arguments, command output, environment variables, or token contents.

## Failure receipts

CCC separates attempt state, logical lane state, and route state. Spark receives one model_unavailable fallback attempt to Luna. Earlier failed attempts remain in the lane receipt, while acceptance depends on each required lane's final valid attempt. Required frontier review has no lower-capability fallback and remains NOT_VERIFIED when unavailable.

Validate a completed lane receipt against actual child rollouts:

    python3 scripts/validate_lane_receipt.py /path/to/lane-receipt.json

Use a non-default session root when needed:

    python3 scripts/validate_lane_receipt.py /path/to/lane-receipt.json \
      --sessions-dir /absolute/path/to/sessions

The validator rejects fake child IDs, parent/model/effort mismatches, unauthorized capability routes, and invalid fallback histories.

Validate a complete route manifest:

    python3 scripts/validate_route_manifest.py /path/to/route-manifest.json

For a declared reroute, bind the terminal previous route:

    python3 scripts/validate_route_manifest.py /path/to/new-route.json \
      --superseded-manifest /path/to/previous-route.json

The route validator rejects duplicate child ownership across independent lanes, required-lane mismatches, incorrect route state, and unbound reroute claims. Reroutes must name the failed bounded lane in `replaces_lane`, retain every other required lane at the same capability, and use fresh child evidence.

### Local A/B observation

On 2026-08-24, a single disposable two-file read-only fixture was run through native Spark/low and Luna/low children with the same task packet:

- Spark: about 15.5 seconds, 227,291 total tokens.
- Luna: about 34.6 seconds, 187,641 total tokens.
- Both found the same core behavioral issues and preserved the requirement-evidence caveat.

This is a capability check, not a general benchmark. It supports Spark as a fast-read preference while showing that faster wall time did not mean fewer tokens in this run.

## Safety boundaries

- The primary agent remains responsible for intent, architecture, integration, and acceptance.
- Child reports are claims, not proof.
- One writer is the default.
- Parallel writers require disjoint ownership and stable interfaces.
- Reviewers are behaviorally read-only unless the host enforces a read-only sandbox.
- Any reviewer mutation invalidates the review.
- Corrections require parent re-verification and a new review verdict.

## Validation

The skill is validated with the Codex skill creator validator:

    uv run --no-project --with pyyaml python \
      "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" .

Run the repository tests:

    python3 -m unittest discover -s tests -v

GitHub Actions runs compile and unit-test checks on pushes to main and pull requests. Static tests verify policy structure and the inspector's security boundary; they do not prove live Codex runtime behavior.

## Design inspiration

CCC is an original workflow inspired by publicly documented ideas from:

- oh-my-codex: bounded delegation, leader ownership, and model lanes.
- Sol Advisor: selective assurance, Luna/Max bounded implementation, and fresh review.
- Superpowers: isolated task packets, per-task execution, and review loops.

See NOTICE.md for links and the attribution boundary.

## License

MIT
