from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_lane_receipt.py"
SPEC = importlib.util.spec_from_file_location("validate_lane_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SPARK = "gpt-5.3-codex-spark"
LUNA = "gpt-5.6-luna"
TERRA = "gpt-5.6-terra"
SOL = "gpt-5.6-sol"
PARENT_ID = "01a0319d-52b7-7853-8840-5ccd6bb436ff"
ROUTE_ID = "01a032b0-0000-7000-8000-000000000001"
NEW_ROUTE_ID = "01a032b0-0000-7000-8000-000000000002"
CHILD_SPARK = "01a032a6-4cdb-7de2-acae-2ee3a8f873fc"
CHILD_LUNA = "01a0329d-c905-7840-8487-e7ca00be04d8"
CHILD_TERRA = "01a032b0-0000-7000-8000-000000000003"
CHILD_SOL = "01a032b0-0000-7000-8000-000000000004"
CHILD_LUNA_MAX = "01a032b0-0000-7000-8000-000000000005"
TURN_SPARK = "01a032b1-0000-7000-8000-000000000001"
TURN_LUNA = "01a032b1-0000-7000-8000-000000000002"
TURN_TERRA = "01a032b1-0000-7000-8000-000000000003"
TURN_SOL = "01a032b1-0000-7000-8000-000000000004"
TURN_LUNA_MAX = "01a032b1-0000-7000-8000-000000000005"
TURN_BY_CHILD = {
    CHILD_SPARK: TURN_SPARK,
    CHILD_LUNA: TURN_LUNA,
    CHILD_TERRA: TURN_TERRA,
    CHILD_SOL: TURN_SOL,
    CHILD_LUNA_MAX: TURN_LUNA_MAX,
}


def write_runtime(
    sessions_dir: Path,
    child_id: str,
    model: str,
    effort: str,
    *,
    parent_id: str = PARENT_ID,
) -> None:
    turn_id = TURN_BY_CHILD[child_id]
    path = sessions_dir / "2026" / "08" / "24" / f"rollout-test-{child_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": child_id,
                "parent_thread_id": parent_id,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "agent_path": "/root/receipt_test",
                            "depth": 1,
                        }
                    }
                },
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "turn_id": turn_id,
                "model": model,
                "effort": effort,
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": turn_id,
                "last_agent_message": "not inspected",
            },
        },
    ]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def attempt(
    number: int,
    state: str,
    cause: str,
    requested_model: str,
    *,
    child_id: str | None,
    resolved_model: str | None,
    effort: str = "low",
    turn_id: str | None = None,
) -> dict:
    if turn_id is None and child_id in TURN_BY_CHILD:
        turn_id = TURN_BY_CHILD[child_id]
    return {
        "number": number,
        "state": state,
        "cause": cause,
        "child_id": child_id,
        "turn_id": turn_id,
        "requested_model": requested_model,
        "resolved_model": resolved_model,
        "reasoning_effort": effort,
    }


def spark_success() -> dict:
    return {
        "schema_version": MODULE.SCHEMA_VERSION,
        "route_id": ROUTE_ID,
        "supersedes_route_id": None,
        "parent_thread_id": PARENT_ID,
        "lane": "repo_scan",
        "capability": "fast",
        "required": True,
        "state": "SUCCEEDED",
        "verification": "VERIFIED",
        "fallback_used": "none",
        "attempts": [
            attempt(
                1,
                "SUCCEEDED",
                "none",
                SPARK,
                child_id=CHILD_SPARK,
                resolved_model=SPARK,
            )
        ],
    }


class LaneReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.sessions_dir = Path(self.tempdir.name)
        write_runtime(self.sessions_dir, CHILD_SPARK, SPARK, "low")
        write_runtime(self.sessions_dir, CHILD_LUNA, LUNA, "low")
        write_runtime(self.sessions_dir, CHILD_TERRA, TERRA, "high")
        write_runtime(self.sessions_dir, CHILD_SOL, SOL, "high")
        write_runtime(self.sessions_dir, CHILD_LUNA_MAX, LUNA, "max")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def validate(self, receipt: dict) -> dict:
        return MODULE.validate_receipt(receipt, self.sessions_dir)

    def test_direct_spark_success(self) -> None:
        self.assertEqual(self.validate(spark_success())["status"], "ok")

    def test_fake_child_id_is_rejected(self) -> None:
        receipt = spark_success()
        receipt["attempts"][0]["child_id"] = "00000000-0000-0000-0000-000000000000"
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_wrong_parent_is_rejected(self) -> None:
        receipt = spark_success()
        receipt["parent_thread_id"] = NEW_ROUTE_ID
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_spark_to_luna_fallback_success(self) -> None:
        receipt = spark_success()
        receipt["fallback_used"] = "spark_to_luna"
        receipt["attempts"] = [
            attempt(1, "FAILED", "model_unavailable", SPARK, child_id=None, resolved_model=None),
            attempt(2, "SUCCEEDED", "none", LUNA, child_id=CHILD_LUNA, resolved_model=LUNA),
        ]
        self.assertEqual(self.validate(receipt)["state"], "SUCCEEDED")

    def test_spark_to_luna_fallback_can_end_failed(self) -> None:
        receipt = spark_success()
        receipt["state"] = "FAILED"
        receipt["verification"] = "NOT_VERIFIED"
        receipt["fallback_used"] = "spark_to_luna"
        receipt["attempts"] = [
            attempt(1, "FAILED", "model_unavailable", SPARK, child_id=None, resolved_model=None),
            attempt(2, "FAILED", "timeout", LUNA, child_id=CHILD_LUNA, resolved_model=None),
        ]
        self.assertEqual(self.validate(receipt)["state"], "FAILED")

    def test_model_unavailable_cannot_have_runtime_evidence(self) -> None:
        receipt = spark_success()
        receipt["fallback_used"] = "spark_to_luna"
        receipt["attempts"] = [
            attempt(
                1,
                "FAILED",
                "model_unavailable",
                SPARK,
                child_id=CHILD_SPARK,
                resolved_model=SPARK,
            ),
            attempt(2, "SUCCEEDED", "none", LUNA, child_id=CHILD_LUNA, resolved_model=LUNA),
        ]
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_timeout_does_not_allow_model_fallback(self) -> None:
        receipt = spark_success()
        receipt["fallback_used"] = "spark_to_luna"
        receipt["attempts"] = [
            attempt(1, "FAILED", "timeout", SPARK, child_id=CHILD_SPARK, resolved_model=None),
            attempt(2, "SUCCEEDED", "none", LUNA, child_id=CHILD_LUNA, resolved_model=LUNA),
        ]
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_frontier_failure_is_not_verified(self) -> None:
        receipt = {
            **spark_success(),
            "lane": "final_review",
            "capability": "frontier",
            "state": "FAILED",
            "verification": "NOT_VERIFIED",
            "attempts": [
                attempt(
                    1,
                    "FAILED",
                    "child_error",
                    SOL,
                    child_id=CHILD_SOL,
                    resolved_model=None,
                    effort="high",
                )
            ],
        }
        self.assertEqual(self.validate(receipt)["verification"], "NOT_VERIFIED")

    def test_failed_attempt_must_match_runtime_model(self) -> None:
        receipt = {
            **spark_success(),
            "lane": "final_review",
            "capability": "frontier",
            "state": "FAILED",
            "verification": "NOT_VERIFIED",
            "attempts": [
                attempt(
                    1,
                    "FAILED",
                    "child_error",
                    SOL,
                    child_id=CHILD_LUNA,
                    resolved_model=None,
                    effort="high",
                )
            ],
        }
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_failed_attempt_must_match_exact_runtime_turn(self) -> None:
        receipt = {
            **spark_success(),
            "lane": "final_review",
            "capability": "frontier",
            "state": "FAILED",
            "verification": "NOT_VERIFIED",
            "attempts": [
                attempt(
                    1,
                    "FAILED",
                    "timeout",
                    SOL,
                    child_id=CHILD_SOL,
                    turn_id=TURN_LUNA,
                    resolved_model=None,
                    effort="high",
                )
            ],
        }
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_failed_attempt_must_match_runtime_effort(self) -> None:
        receipt = {
            **spark_success(),
            "lane": "final_review",
            "capability": "frontier",
            "state": "FAILED",
            "verification": "NOT_VERIFIED",
            "attempts": [
                attempt(
                    1,
                    "FAILED",
                    "evidence_missing",
                    SOL,
                    child_id=CHILD_SOL,
                    resolved_model=None,
                    effort="xhigh",
                )
            ],
        }
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_frontier_cannot_resolve_to_luna(self) -> None:
        receipt = {
            **spark_success(),
            "lane": "final_review",
            "capability": "frontier",
            "attempts": [
                attempt(
                    1,
                    "SUCCEEDED",
                    "none",
                    SOL,
                    child_id=CHILD_LUNA,
                    resolved_model=LUNA,
                    effort="high",
                )
            ],
        }
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_fast_lane_cannot_start_with_luna(self) -> None:
        receipt = spark_success()
        receipt["attempts"][0] = attempt(
            1,
            "SUCCEEDED",
            "none",
            LUNA,
            child_id=CHILD_LUNA,
            resolved_model=LUNA,
        )
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_standard_lane_rejects_spark(self) -> None:
        receipt = {
            **spark_success(),
            "capability": "standard",
        }
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_bounded_implementation_requires_luna_max(self) -> None:
        receipt = {
            **spark_success(),
            "capability": "bounded_implementation",
            "attempts": [
                attempt(
                    1,
                    "SUCCEEDED",
                    "none",
                    LUNA,
                    child_id=CHILD_LUNA_MAX,
                    resolved_model=LUNA,
                    effort="max",
                )
            ],
        }
        self.assertEqual(self.validate(receipt)["state"], "SUCCEEDED")

    def test_optional_failed_lane_is_not_verified(self) -> None:
        receipt = {
            **spark_success(),
            "required": False,
            "state": "FAILED",
            "verification": "VERIFIED",
            "attempts": [
                attempt(
                    1,
                    "FAILED",
                    "child_error",
                    SPARK,
                    child_id=CHILD_SPARK,
                    resolved_model=None,
                )
            ],
        }
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(receipt)

    def test_declared_reroute_uses_new_route_id(self) -> None:
        receipt = {
            **spark_success(),
            "route_id": NEW_ROUTE_ID,
            "supersedes_route_id": ROUTE_ID,
            "lane": "integration_reroute",
            "capability": "standard",
            "attempts": [
                attempt(
                    1,
                    "SUCCEEDED",
                    "none",
                    TERRA,
                    child_id=CHILD_TERRA,
                    resolved_model=TERRA,
                    effort="high",
                )
            ],
        }
        self.assertEqual(self.validate(receipt)["route_id"], NEW_ROUTE_ID)

    def test_route_states_are_mutually_exclusive(self) -> None:
        self.assertEqual(MODULE.derive_route_state(["PENDING"]), "RUNNING")
        self.assertEqual(MODULE.derive_route_state(["RUNNING", "SUCCEEDED"]), "RUNNING")
        self.assertEqual(MODULE.derive_route_state(["SUCCEEDED", "SUCCEEDED"]), "SUCCEEDED")
        self.assertEqual(MODULE.derive_route_state(["SUCCEEDED", "FAILED"]), "PARTIAL")
        self.assertEqual(MODULE.derive_route_state(["FAILED", "FAILED"]), "FAILED")
        with self.assertRaises(MODULE.ReceiptError):
            MODULE.derive_route_state(["READY"])

    def test_previous_failed_attempt_does_not_block_valid_fallback(self) -> None:
        receipt = spark_success()
        receipt["fallback_used"] = "spark_to_luna"
        receipt["attempts"] = [
            attempt(1, "FAILED", "model_unavailable", SPARK, child_id=None, resolved_model=None),
            attempt(2, "SUCCEEDED", "none", LUNA, child_id=CHILD_LUNA, resolved_model=LUNA),
        ]
        self.validate(receipt)
        invalid = copy.deepcopy(receipt)
        invalid["state"] = "FAILED"
        with self.assertRaises(MODULE.ReceiptError):
            self.validate(invalid)


if __name__ == "__main__":
    unittest.main()
