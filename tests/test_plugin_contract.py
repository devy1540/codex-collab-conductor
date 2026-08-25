from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
SKILL_ROOT = SKILLS_ROOT / "codex-collab-conductor"
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
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(
            manifest["description"],
            "Conservative native collaboration for bounded Codex tasks.",
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
                "shortDescription": "Conservative native collaboration for bounded tasks.",
                "longDescription": (
                    "Routes independent work to bounded native agents while keeping scope, "
                    "integration, and acceptance ownership with the parent task."
                ),
                "developerName": "devy1540",
                "category": "Productivity",
                "capabilities": ["Interactive"],
                "defaultPrompt": [
                    "Route independent work to bounded native agents."
                ],
            },
        )

        for forbidden in ("mcpServers", "apps", "hooks", "assets"):
            self.assertNotIn(forbidden, manifest)
        for forbidden in ("mcpServers", "apps", "hooks", "assets"):
            self.assertNotIn(forbidden, manifest["interface"])

    def test_plugin_contains_exactly_one_nested_skill(self) -> None:
        self.assertTrue(SKILLS_ROOT.is_dir())
        skill_dirs = sorted(
            path for path in SKILLS_ROOT.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        self.assertEqual([path.name for path in skill_dirs], ["codex-collab-conductor"])

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
        self.assertGreaterEqual(readme.count("set -eu"), 2)
        self.assertIn('test -f "$TARGET_DIR/.codex-plugin/plugin.json"', readme)
        self.assertIn(
            'test -f "$TARGET_DIR/skills/codex-collab-conductor/SKILL.md"',
            readme,
        )
        self.assertIn('test -f "$TARGET_DIR/SKILL.md"', readme)


if __name__ == "__main__":
    unittest.main()
