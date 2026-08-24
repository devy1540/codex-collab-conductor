from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PolicyContractTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = [
            "SKILL.md",
            "agents/openai.yaml",
            "references/routing.md",
            "references/model-lanes.md",
            "references/task-packets.md",
            "references/assurance.md",
            "references/fallback-states.md",
            "scripts/inspect_child_runtime.py",
            "scripts/validate_lane_receipt.py",
            "scripts/validate_route_manifest.py",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_skill_frontmatter_and_implicit_policy(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertRegex(skill, r"(?s)^---\nname: codex-collab-conductor\n")
        self.assertRegex(skill, r"(?m)^description: .+")
        self.assertIn("allow_implicit_invocation: true", metadata)

    def test_spawn_and_wait_invariants(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        routing = (ROOT / "references/routing.md").read_text(encoding="utf-8")
        self.assertIn("Do not call wait with an empty target list", skill)
        self.assertIn("before any task-specific file read", skill)
        self.assertIn("Confirm a non-empty child ID", routing)

    def test_model_and_fallback_contract(self) -> None:
        models = (ROOT / "references/model-lanes.md").read_text(encoding="utf-8")
        fallback = (ROOT / "references/fallback-states.md").read_text(encoding="utf-8")
        self.assertIn("gpt-5.3-codex-spark", models)
        self.assertIn("gpt-5.6-luna", models)
        self.assertIn("at most once", fallback)
        self.assertIn("NOT_VERIFIED", fallback)
        self.assertIn("ccc-lane-receipt-v1", fallback)
        self.assertIn("ccc-route-manifest-v1", fallback)
        self.assertIn("parent_thread_id", fallback)
        self.assertIn("supersedes_route_id", fallback)
        self.assertIn("replaces_lane", fallback)
        self.assertIn("fresh child", fallback)
        self.assertIn("validate_route_manifest.py", fallback)

    def test_task_packet_and_review_contract(self) -> None:
        packets = (ROOT / "references/task-packets.md").read_text(encoding="utf-8")
        assurance = (ROOT / "references/assurance.md").read_text(encoding="utf-8")
        for heading in [
            "ROLE",
            "OBJECTIVE",
            "SCOPE AND OWNERSHIP",
            "CONSTRAINTS",
            "VERIFICATION",
            "RETURN",
        ]:
            self.assertTrue(re.search(rf"(?m)^{re.escape(heading)}$", packets))
        self.assertIn("Any mutation invalidates the review", assurance)


if __name__ == "__main__":
    unittest.main()
