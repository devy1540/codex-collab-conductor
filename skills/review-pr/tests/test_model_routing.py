from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = SKILL_ROOT / "references" / "model-routing.json"


class ModelRoutingTests(unittest.TestCase):
    def load_contract(self) -> dict:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_every_review_role_has_an_explicit_model_and_effort(self) -> None:
        contract = self.load_contract()
        self.assertEqual(contract["schema_version"], "review-pr-model-routing-v1")
        expected = {
            "recon": ("gpt-5.6-terra", "low"),
            "quality": ("gpt-5.6-terra", "high"),
            "security": ("gpt-5.6-terra", "high"),
            "contract_compatibility": ("gpt-5.6-terra", "high"),
            "data_migration": ("gpt-5.6-terra", "high"),
            "operations_release": ("gpt-5.6-terra", "high"),
            "ui_product_contract": ("gpt-5.6-terra", "high"),
            "challenge": ("gpt-5.6-terra", "high"),
            "synthesis": ("gpt-5.6-terra", "high"),
            "frontier": ("gpt-5.6-sol", "high"),
        }
        actual = {
            role: (route["model"], route["reasoning_effort"])
            for role, route in contract["routes"].items()
        }
        self.assertEqual(actual, expected)

    def test_only_concrete_frontier_review_uses_sol(self) -> None:
        contract = self.load_contract()
        sol_roles = [
            role
            for role, route in contract["routes"].items()
            if route["model"] == "gpt-5.6-sol"
        ]
        self.assertEqual(sol_roles, ["frontier"])
        for route in contract["routes"].values():
            self.assertNotEqual(route["reasoning_effort"], "xhigh")

    def test_frontier_triggers_are_structured_and_evidence_bound(self) -> None:
        frontier = self.load_contract()["routes"]["frontier"]
        self.assertEqual(frontier["max_spawns_per_review"], 1)
        triggers = frontier["required_triggers"]
        self.assertEqual(
            {trigger["id"] for trigger in triggers},
            {
                "high_security_boundary",
                "high_concurrency_or_irreversible_migration",
                "unresolved_high_architecture_or_security_dispute",
            },
        )
        for trigger in triggers:
            self.assertEqual(trigger["severity"], "high")
            self.assertTrue(trigger["requires_file_line"])
            self.assertTrue(trigger["challenge_states"])
            self.assertTrue(trigger["finding_categories"])
            self.assertIn("requires_conflicting_reviews", trigger)

    def test_workflow_roles_match_non_frontier_routes(self) -> None:
        contract = self.load_contract()
        self.assertEqual(
            set(contract["workflow_roles"]),
            set(contract["routes"]) - {"frontier"},
        )

    def test_parent_model_and_effort_are_preserved(self) -> None:
        parent = self.load_contract()["parent_policy"]
        self.assertTrue(parent["preserve_parent_model"])
        self.assertTrue(parent["preserve_parent_reasoning_effort"])

    def test_missing_route_does_not_inherit_the_parent(self) -> None:
        contract = self.load_contract()
        fallback = contract["fallback_policy"]
        self.assertFalse(fallback["inherit_parent"])
        self.assertFalse(fallback["silent_cross_model_fallback"])
        self.assertEqual(fallback["model_unavailable"], "stop_and_report_not_verified")

    def test_skill_loads_the_routing_contract_before_spawn(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("references/model-routing.json", normalized)
        self.assertIn("Every reviewer spawn must set both", normalized)
        self.assertIn("Never rely on parent model inheritance", normalized)
        self.assertIn("frontier_evidence", normalized)
        self.assertIn("matched trigger ID", normalized)
        self.assertIn("Do not spawn `frontier` without", normalized)

    def test_prepare_script_path_is_install_location_independent(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("~/.codex/skills/review-pr", skill)
        self.assertIn("REVIEW_PR_SKILL_ROOT", skill)
        self.assertIn("directory containing this loaded `SKILL.md`", skill)


if __name__ == "__main__":
    unittest.main()
