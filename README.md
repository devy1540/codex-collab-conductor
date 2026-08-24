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

## One skill, four references

This repository contains one actual skill:

- SKILL.md

The remaining files support that skill:

- agents/openai.yaml: Codex UI metadata and implicit invocation policy.
- references/routing.md: solo, parallel-read, delegated-build, and plan-run decisions.
- references/model-lanes.md: Luna, Terra, and Sol example defaults by capability.
- references/task-packets.md: self-contained native child briefs.
- references/assurance.md: parent verification and fresh-review gates.

## Requirements

- A current Codex host with native subagents enabled.
- A native spawn surface that can return child thread IDs.
- Access to the selected models when explicit model routing is used.

Model IDs in this repository are example defaults for current GPT-5.6 Codex environments. The skill requires the capability class, not one permanent model generation.

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

- Fast exploration: GPT-5.6 Luna with low reasoning when available.
- Fully specified bounded implementation: GPT-5.6 Luna with max reasoning when available.
- Judgment-heavy implementation and debugging: GPT-5.6 Terra with high reasoning when available.
- Architecture, security, conflict resolution, and fresh final review: GPT-5.6 Sol with high or xhigh reasoning when available.

Noncritical lanes may use an available equivalent when the preferred model is unavailable. A required independent frontier review must not silently pass through fallback.

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

## Design inspiration

CCC is an original workflow inspired by publicly documented ideas from:

- oh-my-codex: bounded delegation, leader ownership, and model lanes.
- Sol Advisor: selective assurance, Luna/Max bounded implementation, and fresh review.
- Superpowers: isolated task packets, per-task execution, and review loops.

See NOTICE.md for links and the attribution boundary.

## License

MIT
