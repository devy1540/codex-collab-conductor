# Codex Collaboration Conductor

Codex Collaboration Conductor (CCC) is a conservative, implicit Codex skill for
deciding when native subagents are justified by the task shape. The parent keeps scope,
integration, verification, and final acceptance ownership. CCC is not a scheduler or
orchestration service, and it makes no promise of faster execution, task correctness, or
independent assurance.

The same plugin also bundles `review-pr`, an evidence-first, read-only workflow for PR,
branch-diff, and working-tree review. It gives every reviewer role an explicit model and
reasoning effort while preserving the parent model and final acceptance boundary.

## What it provides

- A solo guard for small or tightly coupled work.
- Bounded native read-only and implementation packets when their ownership is explicit.
- A separate assurance choice: parent verification by default, with an optional fresh
  second opinion for material risk.
- Explicit capability-lane routing for fast exploration, bounded implementation, standard
  judgment, and frontier review; see the single detailed policy in
  [`skills/codex-collab-conductor/references/model-lanes.md`](skills/codex-collab-conductor/references/model-lanes.md).
- Optional privacy-safe runtime diagnostics for high-risk routing and fallback
  troubleshooting.
- Evidence-first multi-agent PR review with explicit Terra routes for ordinary reviewers
  and one evidence-gated Sol/high frontier route.

The repository is both a Codex plugin root and two bundled skills. The plugin adds no MCP
server, app, hook, daemon, tmux runtime, custom scheduler, or receipt schema v2.

## Repository layout

The root contains the plugin manifest and public project files:

- `.codex-plugin/plugin.json`
- `README.md`, `LICENSE`, `NOTICE.md`, `.github/`, and `tests/`

The root `SKILL.md`, `agents/`, `references/`, `scripts/`, and `evals/` entries are
tracked compatibility symlinks to the canonical CCC skill for the historical standalone
install path. They do not duplicate or expose `review-pr`; the plugin manifest packages
both nested skills from `./skills/`.

The two bundled skills are:

### `skills/codex-collab-conductor/`

- `skills/codex-collab-conductor/SKILL.md`: the skill entrypoint.
- `skills/codex-collab-conductor/agents/openai.yaml`: Codex UI metadata and implicit
  invocation policy.
- `skills/codex-collab-conductor/references/routing.md`: execution shape and assurance
  decisions.
- `skills/codex-collab-conductor/references/model-lanes.md`: the sole detailed model-routing
  policy.
- `skills/codex-collab-conductor/references/task-packets.md`: self-contained native child
  briefs.
- `skills/codex-collab-conductor/references/assurance.md`: parent verification and optional
  fresh-review gates.
- `skills/codex-collab-conductor/references/fallback-states.md`: optional v1 diagnostic
  state and fallback guidance.
- `skills/codex-collab-conductor/scripts/inspect_child_runtime.py`: allowlisted child routing
  evidence inspector.
- `skills/codex-collab-conductor/scripts/validate_lane_receipt.py`: v1 lane-diagnostic
  validator.
- `skills/codex-collab-conductor/scripts/validate_route_manifest.py`: v1 route-diagnostic
  validator.
- `skills/codex-collab-conductor/evals/canary/`: manual native canary fixtures, playbook,
  and result materials.
- `tests/`: standard-library regression tests for policy structure and diagnostic
  boundaries.

### `skills/review-pr/`

- `skills/review-pr/SKILL.md`: evidence-first PR, branch, and working-tree review workflow.
- `skills/review-pr/agents/openai.yaml`: review skill UI metadata.
- `skills/review-pr/references/model-routing.json`: explicit reviewer model and effort
  contract; ordinary roles use Terra and only evidence-gated frontier review uses Sol/high.
- `skills/review-pr/references/`: reviewer prompts, standards, and risk routing.
- `skills/review-pr/scripts/prepare_review.py`: deterministic review artifact materializer.
- `skills/review-pr/tests/`: artifact and model-routing contract tests.

## Requirements

- A current Codex host with native subagents enabled when a non-solo route is selected.
- A native spawn surface that returns child thread IDs for delegated work.
- Access to the explicitly requested model for the selected capability lane.

## Install

### Plugin installation

Add the public GitHub marketplace, verify the pinned plugin is available, and install it:

    codex plugin marketplace add devy1540/codex-collab-conductor --ref main
    codex plugin list --marketplace devy1540 --available
    codex plugin add codex-collab-conductor@devy1540

The marketplace catalog is tracked at `.agents/plugins/marketplace.json`. It follows
`main`, while the plugin source is pinned to the release tag that matches the manifest
version. The plugin install exposes both `codex-collab-conductor` and `review-pr`. Start a
new Codex task after installation so both bundled skills are loaded.

To pick up a later release, refresh the marketplace snapshot and reinstall the plugin:

    codex plugin marketplace upgrade devy1540
    codex plugin add codex-collab-conductor@devy1540

### Legacy standalone CCC installation

The CCC skill remains compatible with the original direct-clone path. Existing clean
standalone clones can update with an ordinary `git pull`; the root compatibility symlinks
continue to expose `SKILL.md`, `agents/`, `references/`, `scripts/`, and `evals/` from the
canonical CCC skill. This legacy path does not expose the bundled `review-pr`; use the
plugin installation when both skills are required. A fresh standalone CCC install uses the
same path:

    (
      set -eu
      TARGET_DIR="$HOME/.codex/skills/codex-collab-conductor"
      if [ -e "$TARGET_DIR" ] || [ -L "$TARGET_DIR" ]; then
        printf 'Refusing: exact skill target already exists: %s\n' "$TARGET_DIR" >&2
        exit 1
      fi
      mkdir -p "$(dirname "$TARGET_DIR")"
      git clone https://github.com/devy1540/codex-collab-conductor.git "$TARGET_DIR"
      test -f "$TARGET_DIR/.codex-plugin/plugin.json"
      test -f "$TARGET_DIR/SKILL.md"
    )

Restart Codex if the skill does not appear immediately.

Do not keep a separate `review-pr` skill alongside the plugin after verifying a release
install, because duplicate skill names can drift or make source selection ambiguous. Verify
the plugin-cache copy first, then retire the standalone directory with a recoverable move.

## Automatic use

`skills/codex-collab-conductor/agents/openai.yaml` enables implicit invocation. Codex may select this skill when the
request matches the conservative policy, so users do not need to type the skill name on
every task.

`skills/review-pr/agents/openai.yaml` exposes the separate PR-review workflow. It remains
review-only unless the user separately authorizes comments, fixes, commits, or pushes.

One ordinary review, one investigation, and one localized edit remain outside CCC. An
explicitly invoked or more specific workflow skill leads when it applies; CCC supports it
only when that workflow actually needs multiple native lanes.

For stronger personal routing, add a rule like this to the user-level `AGENTS.md`:

    # Native subagent collaboration
    - For coding, debugging, research, or review, apply the
      codex-collab-conductor skill when at least two independent read lanes exist or
      a bounded implementation and optional fresh review materially clarify acceptance.
    - Keep trivial one-step and tightly coupled work solo.
    - For a non-solo route, spawn real native children before task-specific
      investigation. Require child IDs and never call an empty wait.

The repository does not modify `AGENTS.md` automatically.

## Model policy

Task shape and assurance are selected before model routing. The complete, non-duplicated
policy is in [`skills/codex-collab-conductor/references/model-lanes.md`](skills/codex-collab-conductor/references/model-lanes.md). The fast lane is a
low-effort exploration route with one permitted pre-child unavailable/quota cross-model
fallback. Bounded implementation is an explicit quality-first route only for
decision-complete packets, standard judgment is the explicit route for judgment-heavy
integration, debugging, and compatibility work, and frontier review is reserved for
concrete high-risk judgment. The fast fallback is one fallback attempt, not a general
retry budget. Do not infer or claim a resolved model without runtime evidence.

`review-pr` owns its more specific review workflow. It reads
`skills/review-pr/references/model-routing.json` before spawning: recon uses Terra/low,
ordinary reviewers/challenge/synthesis use Terra/high, and Sol/high is capped to one
frontier reviewer with structured high-severity evidence. The parent model is unchanged.

## Optional runtime diagnostics

Receipts and manifests are optional v1 diagnostics, not required workflow artifacts and
not evidence that a child solved its task. A v1 `VERIFIED` value means only that the
allowlisted runtime routing evidence matched the recorded request. It does not establish
task-result correctness.

When diagnostics are needed, the inspector emits only allowlisted thread/turn IDs,
completion, depth, model, and reasoning metadata. It never emits prompts, child
transcripts, tool arguments, command output, environment variables, tokens, or agent
paths.

Inspect one exact child route when local Codex rollout files are available:

    python3 skills/codex-collab-conductor/scripts/inspect_child_runtime.py <child-thread-id>

Use a non-default session root when needed:

    python3 skills/codex-collab-conductor/scripts/inspect_child_runtime.py <child-thread-id> \
      --sessions-dir /absolute/path/to/sessions

The v1 validators remain available for an explicitly requested diagnostic record:

    python3 skills/codex-collab-conductor/scripts/validate_lane_receipt.py /path/to/lane-receipt.json
    python3 skills/codex-collab-conductor/scripts/validate_route_manifest.py /path/to/route-manifest.json

If a diagnostic cannot be represented by the existing v1 schema, omit it rather than
fabricating evidence. Do not treat an omitted diagnostic as proof that routing happened.

## Safety and acceptance boundaries

- The parent owns intent, architecture, integration, diff inspection, and final checks.
- Child reports are claims; tests, runtime evidence, and the parent diff are the proof
  sources available to the parent.
- One writer is the default. Parallel writers require disjoint ownership and stable
  interfaces.
- A reviewer is behaviorally read-only unless an enforced sandbox says otherwise; any
  mutation invalidates that review.
- A required frontier route that cannot use its requested Sol route is
`NOT_VERIFIED`; it is not silently downgraded.
- Final acceptance is parent diff inspection and relevant test reruns. A fresh
  second-opinion review is optional and must be re-checked by the parent.

## Manual native canary

`skills/codex-collab-conductor/evals/canary/` is a privacy-safe manual release gate with six deterministic,
read-only synthetic fixtures: solo guard, parallel fast read, fast route/fallback,
bounded implementation, standard judgment, and frontier seeded-defect review.
Run one functional execution per scenario and record only the fields in the result schema:
execution route, capability lane, assurance route, requested/resolved model, task
`PASS`/`FAIL`, wall time, parent rework, and per-lane verification status. Multi-lane
results keep one privacy-safe routing observation per synthetic lane, without child IDs.

Do not store prompts, child IDs, local paths, or transcripts in canary results. The
canary is not simulated in CI. One canary run does not justify a general correctness or
speed claim. Do not make performance claims until at least five
repeated comparisons against a solo baseline exist; this repository currently makes no
such claim.

## Validation

Validate the skill package:

    uv run --no-project --with pyyaml python \
      "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
      skills/codex-collab-conductor

Validate the review skill package:

    uv run --no-project --with pyyaml python \
      "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
      skills/review-pr

Validate the plugin root:

    uv run --no-project --with pyyaml python \
      "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py" .

Run repository tests:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/review-pr/tests -v

Validate committed canary results against their Draft 2020-12 schema:

    uv run --no-project --with 'jsonschema==4.25.1' \
      python skills/codex-collab-conductor/scripts/validate_canary_results.py

Evaluate the separately defined release gate after the observations are valid. This is
also exposed as the manually dispatched `.github/workflows/release-gate.yml` workflow:

    uv run --no-project --with 'jsonschema==4.25.1' \
      python skills/codex-collab-conductor/scripts/validate_canary_results.py --release-gate

GitHub CI remains static compile, unit-test, CLI, and JSON Schema verification. The
manually dispatched release-gate workflow evaluates committed observations but does not
run native children or claim live runtime behavior.

## Design boundary and license

CCC is an original workflow informed by publicly documented ideas about bounded
delegation, leader ownership, capability routing, and isolated task packets. It does not
require or copy an external orchestration runtime. See `NOTICE.md` for attribution links.

## License

MIT
