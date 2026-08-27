from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "codex-collab-conductor"
CANARY_ROOT = SKILL_ROOT / "evals" / "canary"
SCRIPT = SKILL_ROOT / "scripts" / "validate_canary_results.py"
SPEC = importlib.util.spec_from_file_location("validate_canary_results", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_result(scenario_id: str) -> dict:
    [path] = list((CANARY_ROOT / "results").glob(f"*-{scenario_id}.json"))
    return json.loads(path.read_text(encoding="utf-8"))


class CanaryResultTests(unittest.TestCase):
    def test_v2_schema_separates_execution_capability_and_assurance(self) -> None:
        schema = json.loads((CANARY_ROOT / "result-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "ccc-native-canary-result-v2")
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "ccc-native-canary-result-v2",
        )
        self.assertNotIn("route", schema["properties"])
        for field in ("execution_route", "capability_lane", "assurance_route"):
            self.assertIn(field, schema["required"])
            self.assertIn(field, schema["properties"])
        self.assertIn("lane_observations", schema["required"])
        self.assertIn("lane_observations", schema["properties"])
        for removed in (
            "requested_model",
            "resolved_model",
            "requested_effort",
            "resolved_effort",
            "fallback",
            "failure_class",
            "verification",
        ):
            self.assertNotIn(removed, schema["properties"])

    def test_fixture_v2_routing_contract_matches_each_result(self) -> None:
        for result_path in sorted((CANARY_ROOT / "results").glob("*.json")):
            result = json.loads(result_path.read_text(encoding="utf-8"))
            fixture_path = CANARY_ROOT / "fixtures" / f"{result['scenario_id']}.json"
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            self.assertEqual(fixture["fixture_version"], "ccc-native-canary-fixture-v2")
            self.assertEqual(
                result["fixture_sha256"],
                hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
            )
            route_policy = fixture["route_policy"]
            for field in ("execution_route", "capability_lane", "assurance_route"):
                self.assertEqual(result[field], route_policy[field])
            self.assertEqual(
                [lane["lane"] for lane in result["lane_observations"]],
                route_policy["lanes"],
            )

    def test_parallel_fixture_defines_count_as_cardinality_not_sum(self) -> None:
        fixture = json.loads(
            (CANARY_ROOT / "fixtures" / "parallel-read.json").read_text(encoding="utf-8")
        )
        alpha = fixture["questions"][0]
        self.assertEqual(alpha["operation"], "count")
        self.assertEqual(
            alpha["operation_definition"],
            "Return the number of elements. Do not add the values.",
        )

    def test_failed_v2_parallel_candidate_keeps_its_original_fixture(self) -> None:
        result_path = CANARY_ROOT / "results" / "failed" / "2026-08-27-parallel-read.json"
        fixture_path = (
            CANARY_ROOT / "fixtures" / "history" / "2026-08-27-parallel-read.json"
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["task_result"], "FAIL")
        self.assertEqual(
            result["fixture_sha256"],
            hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        )

    def test_valid_frontier_unavailable_observation_is_structurally_valid(self) -> None:
        payload = load_result("frontier-seeded-defect-review")
        payload.update(observed_child_count=0, task_result="FAIL")
        payload["lane_observations"][0].update(
            resolved_model=None,
            resolved_effort=None,
            fallback="none",
            fallback_cause="none",
            failure_class="model_unavailable",
            verification="NOT_VERIFIED",
        )

        MODULE.validate_semantics(payload)

    def test_failed_observation_still_rejects_impossible_routing_claims(self) -> None:
        frontier = load_result("frontier-seeded-defect-review")
        frontier["task_result"] = "FAIL"

        wrong_model = copy.deepcopy(frontier)
        wrong_model["lane_observations"][0].update(
            resolved_model="gpt-5.3-codex-spark",
            resolved_effort="low",
        )
        zero_child_verified = copy.deepcopy(frontier)
        zero_child_verified["observed_child_count"] = 0
        pre_spawn_failure_with_runtime = copy.deepcopy(frontier)
        pre_spawn_failure_with_runtime["observed_child_count"] = 0
        pre_spawn_failure_with_runtime["lane_observations"][0].update(
            failure_class="model_unavailable",
            verification="NOT_VERIFIED",
        )
        fast_without_fallback = load_result("fast-route-fallback")
        fast_without_fallback["task_result"] = "FAIL"
        fast_without_fallback["lane_observations"][0].update(
            resolved_model="gpt-5.6-luna",
            fallback="none",
            fallback_cause="none",
        )
        eligible_fast_failure_without_fallback = load_result("fast-route-fallback")
        eligible_fast_failure_without_fallback.update(
            observed_child_count=0,
            task_result="FAIL",
        )
        eligible_fast_failure_without_fallback["lane_observations"][0].update(
            resolved_model=None,
            resolved_effort=None,
            fallback="none",
            fallback_cause="none",
            failure_class="quota_denied",
            verification="NOT_VERIFIED",
        )

        for payload in (
            wrong_model,
            zero_child_verified,
            pre_spawn_failure_with_runtime,
            fast_without_fallback,
            eligible_fast_failure_without_fallback,
        ):
            with self.subTest(payload=payload["scenario_id"]):
                with self.assertRaises(ValueError):
                    MODULE.validate_semantics(payload)

    def test_parallel_result_preserves_mixed_lane_resolutions(self) -> None:
        payload = load_result("parallel-read")
        payload.update(task_result="PASS", parent_rework="none")
        payload["lane_observations"][0].update(
            resolved_model="gpt-5.3-codex-spark",
            fallback="none",
            fallback_cause="none",
        )

        MODULE.validate_semantics(payload)
        self.assertEqual(MODULE.release_gate_failures([payload]), [])

    def test_post_child_failure_requires_an_observed_child(self) -> None:
        payload = load_result("frontier-seeded-defect-review")
        payload.update(observed_child_count=0, task_result="FAIL")
        payload["lane_observations"][0].update(
            resolved_model=None,
            resolved_effort=None,
            failure_class="timeout",
            verification="NOT_VERIFIED",
        )

        with self.assertRaises(ValueError):
            MODULE.validate_semantics(payload)

    def test_missing_runtime_evidence_requires_an_observed_child(self) -> None:
        payload = load_result("frontier-seeded-defect-review")
        payload.update(observed_child_count=0, task_result="FAIL")
        payload["lane_observations"][0].update(
            resolved_model=None,
            resolved_effort=None,
            failure_class="evidence_missing",
            verification="NOT_VERIFIED",
        )

        with self.assertRaises(ValueError):
            MODULE.validate_semantics(payload)

    def test_verified_route_can_record_a_later_child_error(self) -> None:
        payload = load_result("frontier-seeded-defect-review")
        payload["task_result"] = "FAIL"
        payload["lane_observations"][0]["failure_class"] = "child_error"

        MODULE.validate_semantics(payload)
        self.assertIn(
            "frontier-seeded-defect-review/review: failure_class=child_error",
            MODULE.release_gate_failures([payload]),
        )

    def test_release_gate_rejects_valid_failed_observation(self) -> None:
        results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((CANARY_ROOT / "results").glob("*.json"))
        ]
        frontier_index = next(
            index
            for index, payload in enumerate(results)
            if payload["scenario_id"] == "frontier-seeded-defect-review"
        )
        failed = copy.deepcopy(results[frontier_index])
        failed.update(observed_child_count=0, task_result="FAIL")
        failed["lane_observations"][0].update(
            resolved_model=None,
            resolved_effort=None,
            failure_class="model_unavailable",
            verification="NOT_VERIFIED",
        )
        results[frontier_index] = failed

        failures = MODULE.release_gate_failures(results)

        self.assertIn("frontier-seeded-defect-review: task_result=FAIL", failures)
        self.assertIn("frontier-seeded-defect-review/review: verification=NOT_VERIFIED", failures)

    def test_release_gate_reports_each_non_task_boundary(self) -> None:
        parallel = load_result("parallel-read")
        parallel.update(
            worktree_unchanged=False,
            observed_child_count=1,
            children_distinct=False,
        )

        failures = MODULE.release_gate_failures([parallel])

        self.assertIn("parallel-read: worktree_unchanged=false", failures)
        self.assertIn("parallel-read: child_count=1/2", failures)
        self.assertIn("parallel-read: children_distinct=false", failures)

    def test_v1_history_is_preserved_outside_the_current_result_set(self) -> None:
        history = sorted((CANARY_ROOT / "results" / "v1").glob("2026-08-25-*.json"))
        fixtures = sorted((CANARY_ROOT / "fixtures" / "v1").glob("*.json"))
        self.assertEqual(len(history), 6)
        self.assertEqual(len(fixtures), 6)
        for path in history:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "ccc-native-canary-result-v1")
            fixture_path = CANARY_ROOT / "fixtures" / "v1" / f"{payload['scenario_id']}.json"
            self.assertEqual(
                payload["fixture_sha256"],
                hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
            )

    def test_release_gate_accepts_current_passing_results(self) -> None:
        results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((CANARY_ROOT / "results").glob("*.json"))
        ]

        self.assertEqual(MODULE.release_gate_failures(results), [])


if __name__ == "__main__":
    unittest.main()
