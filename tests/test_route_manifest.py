from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "codex-collab-conductor"
SCRIPT = SKILL_ROOT / "scripts" / "validate_route_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_route_manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SPARK = "gpt-5.3-codex-spark"
LUNA = "gpt-5.6-luna"
TERRA = "gpt-5.6-terra"
SOL = "gpt-5.6-sol"
PARENT = "01a0319d-52b7-7853-8840-5ccd6bb436ff"
ROUTE = "01a032c0-0000-7000-8000-000000000001"
REROUTE = "01a032c0-0000-7000-8000-000000000002"
SPARK_CHILD = "01a032c1-0000-7000-8000-000000000001"
SOL_CHILD = "01a032c1-0000-7000-8000-000000000002"
LUNA_CHILD = "01a032c1-0000-7000-8000-000000000003"
TERRA_CHILD = "01a032c1-0000-7000-8000-000000000004"
SOL_CHILD_2 = "01a032c1-0000-7000-8000-000000000005"
TERRA_CHILD_2 = "01a032c1-0000-7000-8000-000000000006"
SPARK_TURN = "01a032c2-0000-7000-8000-000000000001"
SOL_TURN = "01a032c2-0000-7000-8000-000000000002"
LUNA_TURN = "01a032c2-0000-7000-8000-000000000003"
TERRA_TURN = "01a032c2-0000-7000-8000-000000000004"
SOL_TURN_2 = "01a032c2-0000-7000-8000-000000000005"
TERRA_TURN_2 = "01a032c2-0000-7000-8000-000000000006"


def write_runtime(root: Path, child: str, turn: str, model: str, effort: str) -> None:
    path = root / "2026" / "08" / "24" / f"rollout-test-{child}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": child,
                "parent_thread_id": PARENT,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "agent_path": "/root/route_test",
                            "depth": 1,
                        }
                    }
                },
            },
        },
        {"type": "turn_context", "payload": {"turn_id": turn, "model": model, "effort": effort}},
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn}},
    ]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def attempt(child: str, turn: str, model: str, effort: str) -> dict:
    return {
        "number": 1,
        "state": "SUCCEEDED",
        "cause": "none",
        "child_id": child,
        "turn_id": turn,
        "requested_model": model,
        "resolved_model": model,
        "reasoning_effort": effort,
    }


def receipt(
    route_id: str,
    supersedes: str | None,
    lane: str,
    capability: str,
    child: str,
    turn: str,
    model: str,
    effort: str,
    *,
    state: str = "SUCCEEDED",
    verification: str = "VERIFIED",
) -> dict:
    return {
        "schema_version": "ccc-lane-receipt-v1",
        "route_id": route_id,
        "supersedes_route_id": supersedes,
        "parent_thread_id": PARENT,
        "lane": lane,
        "capability": capability,
        "required": True,
        "state": state,
        "verification": verification,
        "fallback_used": "none",
        "attempts": [attempt(child, turn, model, effort)],
    }


class RouteManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.sessions = Path(self.tempdir.name)
        write_runtime(self.sessions, SPARK_CHILD, SPARK_TURN, SPARK, "low")
        write_runtime(self.sessions, SOL_CHILD, SOL_TURN, SOL, "high")
        write_runtime(self.sessions, LUNA_CHILD, LUNA_TURN, LUNA, "max")
        write_runtime(self.sessions, TERRA_CHILD, TERRA_TURN, TERRA, "high")
        write_runtime(self.sessions, SOL_CHILD_2, SOL_TURN_2, SOL, "high")
        write_runtime(self.sessions, TERRA_CHILD_2, TERRA_TURN_2, TERRA, "high")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def dual_manifest(self) -> dict:
        lanes = [
            receipt(ROUTE, None, "repo_scan", "fast", SPARK_CHILD, SPARK_TURN, SPARK, "low"),
            receipt(ROUTE, None, "final_review", "frontier", SOL_CHILD, SOL_TURN, SOL, "high"),
        ]
        return {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": ROUTE,
            "supersedes_route_id": None,
            "replaces_lane": None,
            "parent_thread_id": PARENT,
            "state": "SUCCEEDED",
            "required_lanes": ["repo_scan", "final_review"],
            "lanes": lanes,
        }

    def test_dual_route_success(self) -> None:
        result = MODULE.validate_route_manifest(self.dual_manifest(), self.sessions)
        self.assertEqual(result["state"], "SUCCEEDED")

    def test_one_child_cannot_prove_two_lanes(self) -> None:
        manifest = self.dual_manifest()
        second = manifest["lanes"][1]
        second["attempts"][0] = copy.deepcopy(manifest["lanes"][0]["attempts"][0])
        second["capability"] = "fast"
        with self.assertRaises(MODULE.RouteError):
            MODULE.validate_route_manifest(manifest, self.sessions)

    def test_route_state_mismatch_fails(self) -> None:
        manifest = self.dual_manifest()
        manifest["state"] = "FAILED"
        with self.assertRaises(MODULE.RouteError):
            MODULE.validate_route_manifest(manifest, self.sessions)

    def test_missing_superseded_manifest_fails(self) -> None:
        manifest = self.dual_manifest()
        manifest["route_id"] = REROUTE
        manifest["supersedes_route_id"] = ROUTE
        manifest["replaces_lane"] = "repo_scan"
        for lane in manifest["lanes"]:
            lane["route_id"] = REROUTE
            lane["supersedes_route_id"] = ROUTE
        with self.assertRaises(MODULE.RouteError):
            MODULE.validate_route_manifest(manifest, self.sessions)

    def test_valid_bounded_to_standard_reroute(self) -> None:
        old_lane = receipt(
            ROUTE,
            None,
            "bounded_build",
            "bounded_implementation",
            LUNA_CHILD,
            LUNA_TURN,
            LUNA,
            "max",
            state="FAILED",
            verification="NOT_VERIFIED",
        )
        old_lane["attempts"][0]["state"] = "FAILED"
        old_lane["attempts"][0]["cause"] = "child_error"
        old_lane["attempts"][0]["resolved_model"] = None
        previous = {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": ROUTE,
            "supersedes_route_id": None,
            "replaces_lane": None,
            "parent_thread_id": PARENT,
            "state": "FAILED",
            "required_lanes": ["bounded_build"],
            "lanes": [old_lane],
        }
        new_lane = receipt(
            REROUTE,
            ROUTE,
            "integration_reroute",
            "standard",
            TERRA_CHILD,
            TERRA_TURN,
            TERRA,
            "high",
        )
        current = {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": REROUTE,
            "supersedes_route_id": ROUTE,
            "replaces_lane": "bounded_build",
            "parent_thread_id": PARENT,
            "state": "SUCCEEDED",
            "required_lanes": ["integration_reroute"],
            "lanes": [new_lane],
        }
        result = MODULE.validate_route_manifest(current, self.sessions, previous)
        self.assertEqual(result["route_id"], REROUTE)

    def test_reroute_cannot_drop_required_frontier_lane(self) -> None:
        previous = self._failed_bounded_and_frontier_manifest()
        new_lane = receipt(
            REROUTE,
            ROUTE,
            "integration_reroute",
            "standard",
            TERRA_CHILD,
            TERRA_TURN,
            TERRA,
            "high",
        )
        current = {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": REROUTE,
            "supersedes_route_id": ROUTE,
            "replaces_lane": "bounded_build",
            "parent_thread_id": PARENT,
            "state": "SUCCEEDED",
            "required_lanes": ["integration_reroute"],
            "lanes": [new_lane],
        }
        with self.assertRaises(MODULE.RouteError):
            MODULE.validate_route_manifest(current, self.sessions, previous)

    def test_reroute_reproves_retained_frontier_with_fresh_child(self) -> None:
        previous = self._failed_bounded_and_frontier_manifest()
        lanes = [
            receipt(
                REROUTE,
                ROUTE,
                "integration_reroute",
                "standard",
                TERRA_CHILD,
                TERRA_TURN,
                TERRA,
                "high",
            ),
            receipt(
                REROUTE,
                ROUTE,
                "final_review",
                "frontier",
                SOL_CHILD_2,
                SOL_TURN_2,
                SOL,
                "high",
            ),
        ]
        current = {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": REROUTE,
            "supersedes_route_id": ROUTE,
            "replaces_lane": "bounded_build",
            "parent_thread_id": PARENT,
            "state": "SUCCEEDED",
            "required_lanes": ["integration_reroute", "final_review"],
            "lanes": lanes,
        }
        result = MODULE.validate_route_manifest(current, self.sessions, previous)
        self.assertEqual(result["state"], "SUCCEEDED")

    def test_reroute_cannot_downgrade_retained_frontier_capability(self) -> None:
        previous = self._failed_bounded_and_frontier_manifest()
        lanes = [
            receipt(
                REROUTE,
                ROUTE,
                "integration_reroute",
                "standard",
                TERRA_CHILD,
                TERRA_TURN,
                TERRA,
                "high",
            ),
            receipt(
                REROUTE,
                ROUTE,
                "final_review",
                "standard",
                TERRA_CHILD_2,
                TERRA_TURN_2,
                TERRA,
                "high",
            ),
        ]
        current = {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": REROUTE,
            "supersedes_route_id": ROUTE,
            "replaces_lane": "bounded_build",
            "parent_thread_id": PARENT,
            "state": "SUCCEEDED",
            "required_lanes": ["integration_reroute", "final_review"],
            "lanes": lanes,
        }
        with self.assertRaises(MODULE.RouteError):
            MODULE.validate_route_manifest(current, self.sessions, previous)

    def test_reroute_rejects_reused_child_evidence(self) -> None:
        previous = self._failed_bounded_and_frontier_manifest()
        lanes = [
            receipt(
                REROUTE,
                ROUTE,
                "integration_reroute",
                "standard",
                TERRA_CHILD,
                TERRA_TURN,
                TERRA,
                "high",
            ),
            receipt(
                REROUTE,
                ROUTE,
                "final_review",
                "frontier",
                SOL_CHILD,
                SOL_TURN,
                SOL,
                "high",
            ),
        ]
        current = {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": REROUTE,
            "supersedes_route_id": ROUTE,
            "replaces_lane": "bounded_build",
            "parent_thread_id": PARENT,
            "state": "SUCCEEDED",
            "required_lanes": ["integration_reroute", "final_review"],
            "lanes": lanes,
        }
        with self.assertRaises(MODULE.RouteError):
            MODULE.validate_route_manifest(current, self.sessions, previous)

    def _failed_bounded_and_frontier_manifest(self) -> dict:
        bounded = receipt(
            ROUTE,
            None,
            "bounded_build",
            "bounded_implementation",
            LUNA_CHILD,
            LUNA_TURN,
            LUNA,
            "max",
            state="FAILED",
            verification="NOT_VERIFIED",
        )
        frontier = receipt(
            ROUTE,
            None,
            "final_review",
            "frontier",
            SOL_CHILD,
            SOL_TURN,
            SOL,
            "high",
            state="FAILED",
            verification="NOT_VERIFIED",
        )
        for lane in (bounded, frontier):
            lane["attempts"][0]["state"] = "FAILED"
            lane["attempts"][0]["cause"] = "child_error"
            lane["attempts"][0]["resolved_model"] = None
        return {
            "schema_version": MODULE.SCHEMA_VERSION,
            "route_id": ROUTE,
            "supersedes_route_id": None,
            "replaces_lane": None,
            "parent_thread_id": PARENT,
            "state": "FAILED",
            "required_lanes": ["bounded_build", "final_review"],
            "lanes": [bounded, frontier],
        }


if __name__ == "__main__":
    unittest.main()
