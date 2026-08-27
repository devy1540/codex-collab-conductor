from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
SKILL_ROOT = SKILLS_ROOT / "codex-collab-conductor"
REVIEW_SKILL_ROOT = SKILLS_ROOT / "review-pr"
MANIFEST_PATH = REPO_ROOT / ".codex-plugin" / "plugin.json"


class PluginContractTests(unittest.TestCase):
    def test_manifest_has_validated_public_metadata(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            set(manifest),
            {
                "name",
                "version",
                "description",
                "author",
                "homepage",
                "repository",
                "license",
                "skills",
                "interface",
            },
        )
        self.assertEqual(manifest["name"], "codex-collab-conductor")
        self.assertEqual(manifest["version"], "0.3.0")
        self.assertEqual(
            manifest["description"],
            "Conservative native collaboration and evidence-first PR review for Codex.",
        )
        self.assertEqual(manifest["author"], {"name": "devy1540"})
        self.assertEqual(
            manifest["homepage"],
            "https://github.com/devy1540/codex-collab-conductor",
        )
        self.assertEqual(
            manifest["repository"],
            "https://github.com/devy1540/codex-collab-conductor",
        )
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(
            manifest["interface"],
            {
                "displayName": "Codex Collab Conductor",
                "shortDescription": "Native collaboration and evidence-first PR review.",
                "longDescription": (
                    "Routes bounded native agents and provides read-only multi-agent PR review "
                    "while keeping integration and acceptance with the parent task."
                ),
                "developerName": "devy1540",
                "category": "Productivity",
                "capabilities": ["Interactive"],
                "defaultPrompt": [
                    "Route independent work to bounded native agents.",
                    "Review this exact PR or branch diff without editing.",
                ],
            },
        )

        for forbidden in ("mcpServers", "apps", "hooks", "assets"):
            self.assertNotIn(forbidden, manifest)
        for forbidden in ("mcpServers", "apps", "hooks", "assets"):
            self.assertNotIn(forbidden, manifest["interface"])

    def test_plugin_contains_two_nested_skills(self) -> None:
        self.assertTrue(SKILLS_ROOT.is_dir())
        skill_dirs = sorted(
            path for path in SKILLS_ROOT.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        self.assertEqual(
            [path.name for path in skill_dirs],
            ["codex-collab-conductor", "review-pr"],
        )

    def test_nested_skill_and_resources_exist_without_root_duplicates(self) -> None:
        required_files = [
            "SKILL.md",
            "agents/openai.yaml",
            "references/assurance.md",
            "references/fallback-states.md",
            "references/model-lanes.md",
            "references/routing.md",
            "references/task-packets.md",
            "scripts/inspect_child_runtime.py",
            "scripts/validate_canary_results.py",
            "scripts/validate_lane_receipt.py",
            "scripts/validate_route_manifest.py",
            "evals/canary/README.md",
            "evals/canary/playbook.md",
            "evals/canary/result-schema.json",
            "evals/canary/result-template.json",
        ]
        for relative in required_files:
            self.assertTrue((SKILL_ROOT / relative).is_file(), relative)

        review_required_files = [
            "SKILL.md",
            "agents/openai.yaml",
            "references/model-routing.json",
            "references/review-standards.md",
            "references/reviewer-roles.md",
            "references/risk-routing.md",
            "scripts/prepare_review.py",
            "tests/test_model_routing.py",
            "tests/test_prepare_review.py",
        ]
        for relative in review_required_files:
            self.assertTrue((REVIEW_SKILL_ROOT / relative).is_file(), relative)
        self.assertNotIn(
            "~/.codex/skills/review-pr",
            (REVIEW_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )

    def test_root_compatibility_symlinks_and_install_docs(self) -> None:
        compatibility_links = {
            "SKILL.md": "skills/codex-collab-conductor/SKILL.md",
            "agents": "skills/codex-collab-conductor/agents",
            "references": "skills/codex-collab-conductor/references",
            "scripts": "skills/codex-collab-conductor/scripts",
            "evals": "skills/codex-collab-conductor/evals",
        }
        for relative, target in compatibility_links.items():
            link = REPO_ROOT / relative
            self.assertTrue(link.is_symlink(), relative)
            self.assertEqual(os.readlink(link), target, relative)
            self.assertTrue(link.exists(), relative)

        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        normalized_readme = " ".join(readme.split())
        self.assertIn("ordinary `git pull`", normalized_readme)
        self.assertIn("original direct-clone path", normalized_readme)
        self.assertGreaterEqual(readme.count("set -eu"), 1)
        self.assertIn(
            "codex plugin marketplace add devy1540/codex-collab-conductor --ref main",
            readme,
        )
        self.assertIn(
            "codex plugin add codex-collab-conductor@devy1540",
            readme,
        )
        self.assertIn('test -f "$TARGET_DIR/SKILL.md"', readme)
        self.assertIn("skills/review-pr/", readme)

    def test_public_marketplace_contract(self) -> None:
        marketplace_path = REPO_ROOT / ".agents/plugins/marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))

        self.assertEqual(marketplace["name"], "devy1540")
        self.assertEqual(
            marketplace["interface"],
            {"displayName": "devy1540 Plugins"},
        )
        self.assertEqual(len(marketplace["plugins"]), 1)

        plugin = marketplace["plugins"][0]
        self.assertEqual(plugin["name"], "codex-collab-conductor")
        self.assertEqual(
            plugin["source"],
            {
                "source": "url",
                "url": "https://github.com/devy1540/codex-collab-conductor.git",
                "ref": "v0.3.0",
            },
        )
        self.assertEqual(
            plugin["policy"],
            {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
        )
        self.assertEqual(plugin["category"], "Productivity")


if __name__ == "__main__":
    unittest.main()
