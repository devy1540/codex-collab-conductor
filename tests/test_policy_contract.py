from __future__ import annotations

import copy
import hashlib
import json
import re
import runpy
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "codex-collab-conductor"


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
            "scripts/validate_canary_results.py",
        ]
        for relative in required:
            self.assertTrue((SKILL_ROOT / relative).is_file(), relative)

    def test_canary_package_is_complete_and_synthetic(self) -> None:
        canary = SKILL_ROOT / "evals" / "canary"
        required = [
            "README.md",
            "playbook.md",
            "result-schema.json",
            "result-template.json",
            "fixtures/solo-guard.json",
            "fixtures/parallel-read.json",
            "fixtures/fast-route-fallback.json",
            "fixtures/bounded-implementation.json",
            "fixtures/standard-judgment.json",
            "fixtures/frontier-seeded-defect-review.json",
        ]
        for relative in required:
            self.assertTrue((canary / relative).is_file(), relative)

        schema = json.loads((canary / "result-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "ccc-native-canary-result-v2")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "scenario_id",
                "fixture_sha256",
                "execution_route",
                "capability_lane",
                "assurance_route",
                "expected_child_count",
                "observed_child_count",
                "children_distinct",
                "worktree_unchanged",
                "lane_observations",
                "task_result",
                "wall_time_ms",
                "parent_rework",
            },
        )
        scenario_ids = set(schema["properties"]["scenario_id"]["enum"])
        fixture_ids = set()
        for fixture in sorted((canary / "fixtures").glob("*.json")):
            payload = json.loads(fixture.read_text(encoding="utf-8"))
            fixture_ids.add(payload["scenario_id"])
            self.assertEqual(payload["data_classification"], "synthetic-public")
            self.assertEqual(payload["mode"], "read-only")
            text = fixture.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text)
            self.assertNotIn("child_id", text)
        self.assertEqual(fixture_ids, scenario_ids)

        template = json.loads((canary / "result-template.json").read_text(encoding="utf-8"))
        self.assertEqual(set(template), set(schema["properties"]))
        self.assertIsNone(template["scenario_id"])
        for forbidden in ["prompt", "child_id", "turn_id", "local_path", "transcript"]:
            self.assertNotIn(forbidden, schema["properties"])

        fixture_hashes = {
            path.stem: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (canary / "fixtures").glob("*.json")
        }
        results = sorted((canary / "results").glob("*.json"))
        self.assertEqual(len(results), len(scenario_ids))
        observed_results = set()
        by_scenario = {}
        for result_path in results:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), set(schema["properties"]))
            scenario = payload["scenario_id"]
            observed_results.add(scenario)
            by_scenario[scenario] = payload
            self.assertEqual(payload["fixture_sha256"], fixture_hashes[scenario])
            self.assertTrue(payload["worktree_unchanged"])
            self.assertEqual(payload["observed_child_count"], payload["expected_child_count"])
            text = result_path.read_text(encoding="utf-8")
            for forbidden in ["/Users/", "child_id", "turn_id", "prompt", "transcript"]:
                self.assertNotIn(forbidden, text)
        self.assertEqual(observed_results, scenario_ids)
        solo = by_scenario["solo-guard"]
        self.assertEqual(solo["execution_route"], "solo")
        self.assertIsNone(solo["capability_lane"])
        self.assertEqual(solo["assurance_route"], "parent-check")
        self.assertEqual((solo["expected_child_count"], solo["observed_child_count"]), (0, 0))
        self.assertIsNone(solo["children_distinct"])
        self.assertEqual(solo["lane_observations"], [])

        parallel = by_scenario["parallel-read"]
        self.assertEqual(parallel["execution_route"], "parallel-read")
        self.assertEqual(parallel["capability_lane"], "fast")
        self.assertEqual(parallel["assurance_route"], "parent-check")
        self.assertEqual(
            (parallel["expected_child_count"], parallel["observed_child_count"]),
            (2, 2),
        )
        self.assertTrue(parallel["children_distinct"])
        self.assertEqual(parallel["task_result"], "PASS")
        self.assertEqual(parallel["parent_rework"], "none")
        self.assertEqual(
            [lane["lane"] for lane in parallel["lane_observations"]],
            ["alpha", "beta"],
        )

        fast = by_scenario["fast-route-fallback"]
        self.assertIsNone(fast["execution_route"])
        self.assertEqual(fast["capability_lane"], "fast")
        self.assertEqual((fast["expected_child_count"], fast["observed_child_count"]), (1, 1))
        self.assertIsNone(fast["children_distinct"])
        self.assertEqual(fast["lane_observations"][0]["fallback"], "spark_to_luna")
        self.assertEqual(fast["lane_observations"][0]["fallback_cause"], "quota_denied")
        self.assertEqual(fast["lane_observations"][0]["failure_class"], "none")

        bounded = by_scenario["bounded-implementation"]
        self.assertEqual(bounded["execution_route"], "delegated-build")
        self.assertEqual(bounded["capability_lane"], "bounded_implementation")
        self.assertEqual(bounded["assurance_route"], "parent-check")
        bounded_lane = bounded["lane_observations"][0]
        self.assertEqual(bounded_lane["requested_model"], "gpt-5.6-luna")
        self.assertEqual(bounded_lane["requested_effort"], "max")
        self.assertEqual(bounded_lane["fallback"], "none")

        judgment = by_scenario["standard-judgment"]
        self.assertIsNone(judgment["execution_route"])
        self.assertEqual(judgment["capability_lane"], "standard")
        judgment_lane = judgment["lane_observations"][0]
        self.assertEqual(judgment_lane["requested_model"], "gpt-5.6-terra")
        self.assertEqual(judgment_lane["requested_effort"], "high")
        self.assertEqual(judgment_lane["fallback"], "none")
        self.assertEqual(judgment_lane["failure_class"], "none")

        frontier = by_scenario["frontier-seeded-defect-review"]
        self.assertIsNone(frontier["execution_route"])
        self.assertEqual(frontier["capability_lane"], "frontier")
        self.assertEqual(frontier["assurance_route"], "independent-review")
        frontier_lane = frontier["lane_observations"][0]
        self.assertEqual(frontier_lane["requested_model"], "gpt-5.6-sol")
        self.assertEqual(frontier_lane["resolved_model"], "gpt-5.6-sol")
        self.assertEqual(frontier_lane["requested_effort"], "high")
        self.assertEqual(frontier_lane["resolved_effort"], "high")
        self.assertEqual(frontier_lane["fallback"], "none")

        validate_semantics = runpy.run_path(
            str(SKILL_ROOT / "scripts" / "validate_canary_results.py")
        )["validate_semantics"]
        for payload in by_scenario.values():
            validate_semantics(payload)

        invalid_fast = copy.deepcopy(fast)
        invalid_fast["capability_lane"] = "frontier"
        with self.assertRaises(ValueError):
            validate_semantics(invalid_fast)

        invalid_frontier = copy.deepcopy(frontier)
        invalid_frontier["lane_observations"][0]["verification"] = "NOT_VERIFIED"
        with self.assertRaises(ValueError):
            validate_semantics(invalid_frontier)

        invalid_bounded = copy.deepcopy(bounded)
        invalid_bounded["lane_observations"][0]["resolved_model"] = "gpt-5.6-sol"
        with self.assertRaises(ValueError):
            validate_semantics(invalid_bounded)

        invalid_judgment = copy.deepcopy(judgment)
        invalid_judgment["lane_observations"][0]["requested_effort"] = "xhigh"
        with self.assertRaises(ValueError):
            validate_semantics(invalid_judgment)

        leaked_identifier = copy.deepcopy(parallel)
        leaked_identifier["lane_observations"][0]["resolved_model"] = (
            "00000000-0000-0000-0000-000000000000"
        )
        with self.assertRaises(ValueError):
            validate_semantics(leaked_identifier)

    def test_model_policy_is_the_only_concrete_route_source(self) -> None:
        model_policy = (SKILL_ROOT / "references/model-lanes.md").read_text(encoding="utf-8")
        self.assertIn("gpt-5.3-codex-spark", model_policy)
        self.assertIn("gpt-5.6-luna", model_policy)
        self.assertIn("gpt-5.6-terra", model_policy)
        self.assertIn("gpt-5.6-sol", model_policy)
        self.assertIn("reasoning effort `max`", model_policy)
        self.assertIn("reasoning effort `high`", model_policy)
        self.assertIn("pre-child", model_policy)
        self.assertIn("NOT_VERIFIED", model_policy)
        self.assertIn("xhigh", model_policy)

        concrete_models = (
            "gpt-5.3-codex-spark",
            "gpt-5.6-luna",
            "gpt-5.6-terra",
            "gpt-5.6-sol",
        )
        for relative in [
            "README.md",
            "SKILL.md",
            "references/routing.md",
            "references/fallback-states.md",
            "references/assurance.md",
            "references/task-packets.md",
        ]:
            base = REPO_ROOT if relative == "README.md" else SKILL_ROOT
            content = (base / relative).read_text(encoding="utf-8")
            for model in concrete_models:
                self.assertNotIn(model, content, f"{model} duplicated in {relative}")

    def test_skill_frontmatter_and_implicit_policy(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertRegex(skill, r"(?s)^---\nname: codex-collab-conductor\n")
        self.assertRegex(skill, r"(?m)^description: .+")
        self.assertIn("allow_implicit_invocation: true", metadata)
        self.assertIn("at least two independent lanes", skill)
        self.assertIn("more specific skill", skill)
        self.assertIn("bounded implementation followed by a deferred fresh second opinion", metadata)

    def test_spawn_and_wait_invariants(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        routing = (SKILL_ROOT / "references/routing.md").read_text(encoding="utf-8")
        self.assertIn("Do not call wait with an empty target list", skill)
        self.assertIn("before any task-specific file read", skill)
        self.assertIn("execution lane", skill)
        self.assertRegex(skill, r"after\s+implementation and parent verification")
        self.assertIn("Confirm a non-empty child ID", routing)

    def test_model_and_fallback_contract(self) -> None:
        models = (SKILL_ROOT / "references/model-lanes.md").read_text(encoding="utf-8")
        fallback = (SKILL_ROOT / "references/fallback-states.md").read_text(encoding="utf-8")
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
        packets = (SKILL_ROOT / "references/task-packets.md").read_text(encoding="utf-8")
        assurance = (SKILL_ROOT / "references/assurance.md").read_text(encoding="utf-8")
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
