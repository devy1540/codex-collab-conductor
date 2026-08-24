#!/usr/bin/env python3
"""Validate one completed CCC lane receipt against actual child rollouts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from inspect_child_runtime import (  # noqa: E402
    InspectorError,
    inspect_child_identity,
    inspect_thread,
    inspect_turn_context,
)


SCHEMA_VERSION = "ccc-lane-receipt-v1"
THREAD_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
LANE_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
MODELS = {
    "gpt-5.3-codex-spark",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
CAUSES = {"none", "capacity", "model_unavailable", "timeout", "child_error", "evidence_missing"}
CAPABILITIES = {"fast", "bounded_implementation", "standard", "frontier"}
CAPABILITY_ROUTES = {
    "fast": {
        ("gpt-5.3-codex-spark", "low"),
    },
    "bounded_implementation": {
        ("gpt-5.6-luna", "max"),
    },
    "standard": {
        ("gpt-5.6-terra", "high"),
    },
    "frontier": {
        ("gpt-5.6-sol", "high"),
        ("gpt-5.6-sol", "xhigh"),
    },
}


class ReceiptError(Exception):
    pass


def _default_sessions_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "sessions"
    return Path.home() / ".codex" / "sessions"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptError(message)


def _valid_thread_id(value: Any) -> bool:
    return isinstance(value, str) and bool(THREAD_ID_RE.fullmatch(value))


def _validate_attempt(
    attempt: Any,
    number: int,
    capability: str,
    fallback_used: str,
    parent_thread_id: str,
    sessions_dir: Path,
) -> None:
    _require(isinstance(attempt, dict), "attempt must be an object")
    expected_keys = {
        "number",
        "state",
        "cause",
        "child_id",
        "turn_id",
        "requested_model",
        "resolved_model",
        "reasoning_effort",
    }
    _require(set(attempt) == expected_keys, "attempt keys do not match schema")
    _require(attempt["number"] == number, "attempt numbers must be sequential")
    _require(attempt["state"] in {"SUCCEEDED", "FAILED"}, "invalid attempt state")
    _require(attempt["cause"] in CAUSES, "invalid attempt cause")
    _require(attempt["requested_model"] in MODELS, "invalid requested model")
    _require(
        attempt["resolved_model"] is None or attempt["resolved_model"] in MODELS,
        "invalid resolved model",
    )
    _require(attempt["reasoning_effort"] in EFFORTS, "invalid reasoning effort")

    expected_routes = CAPABILITY_ROUTES[capability]
    if capability == "fast" and fallback_used == "spark_to_luna" and number == 2:
        expected_routes = {("gpt-5.6-luna", "low")}
    _require(
        (attempt["requested_model"], attempt["reasoning_effort"]) in expected_routes,
        "requested model and effort do not match capability attempt",
    )
    _require(
        attempt["resolved_model"] is None
        or attempt["resolved_model"] == attempt["requested_model"],
        "resolved model must match requested model",
    )

    if attempt["state"] == "SUCCEEDED":
        _require(attempt["cause"] == "none", "successful attempt must use cause none")
        _require(_valid_thread_id(attempt["child_id"]), "successful attempt requires child id")
        _require(_valid_thread_id(attempt["turn_id"]), "successful attempt requires turn id")
        _require(attempt["resolved_model"] is not None, "successful attempt requires resolved model")
        try:
            evidence = inspect_thread(
                attempt["child_id"],
                sessions_dir,
                attempt["turn_id"],
            )
        except InspectorError as error:
            raise ReceiptError("runtime evidence unavailable") from error
        _require(evidence["parent_thread_id"] == parent_thread_id, "runtime parent mismatch")
        _require(evidence["model"] == attempt["resolved_model"], "runtime model mismatch")
        _require(
            evidence["reasoning_effort"] == attempt["reasoning_effort"],
            "runtime reasoning mismatch",
        )
        return

    _require(attempt["cause"] != "none", "failed attempt requires a failure cause")
    _require(
        attempt["child_id"] is None or _valid_thread_id(attempt["child_id"]),
        "failed attempt child id is invalid",
    )
    if attempt["cause"] in {"model_unavailable", "capacity"}:
        _require(attempt["child_id"] is None, "pre-spawn failure cannot have child id")
        _require(attempt["turn_id"] is None, "pre-spawn failure cannot have turn id")
        _require(attempt["resolved_model"] is None, "pre-spawn failure cannot resolve model")
        return
    _require(_valid_thread_id(attempt["child_id"]), "post-spawn failure requires child id")
    _require(_valid_thread_id(attempt["turn_id"]), "post-spawn failure requires turn id")
    _require(attempt["resolved_model"] is None, "failed attempt cannot claim resolved model")
    try:
        evidence = inspect_turn_context(
            attempt["child_id"],
            sessions_dir,
            attempt["turn_id"],
        )
    except InspectorError as error:
        raise ReceiptError("child runtime context unavailable") from error
    _require(evidence["parent_thread_id"] == parent_thread_id, "runtime parent mismatch")
    _require(evidence["model"] == attempt["requested_model"], "runtime model mismatch")
    _require(
        evidence["reasoning_effort"] == attempt["reasoning_effort"],
        "runtime reasoning mismatch",
    )


def validate_receipt(receipt: Any, sessions_dir: Path) -> dict[str, Any]:
    _require(isinstance(receipt, dict), "receipt must be an object")
    expected_keys = {
        "schema_version",
        "route_id",
        "supersedes_route_id",
        "parent_thread_id",
        "lane",
        "capability",
        "required",
        "state",
        "verification",
        "fallback_used",
        "attempts",
    }
    _require(set(receipt) == expected_keys, "receipt keys do not match schema")
    _require(receipt["schema_version"] == SCHEMA_VERSION, "unsupported receipt schema")
    _require(_valid_thread_id(receipt["route_id"]), "invalid route id")
    _require(
        receipt["supersedes_route_id"] is None
        or _valid_thread_id(receipt["supersedes_route_id"]),
        "invalid superseded route id",
    )
    _require(
        receipt["supersedes_route_id"] != receipt["route_id"],
        "route cannot supersede itself",
    )
    _require(_valid_thread_id(receipt["parent_thread_id"]), "invalid parent thread id")
    _require(isinstance(receipt["lane"], str) and LANE_RE.fullmatch(receipt["lane"]), "invalid lane")
    _require(receipt["capability"] in CAPABILITIES, "invalid capability")
    _require(isinstance(receipt["required"], bool), "required must be boolean")
    _require(receipt["state"] in {"SUCCEEDED", "FAILED"}, "completed lane state is invalid")
    _require(receipt["verification"] in {"VERIFIED", "NOT_VERIFIED"}, "invalid verification")
    _require(receipt["fallback_used"] in {"none", "spark_to_luna"}, "invalid fallback")
    _require(isinstance(receipt["attempts"], list) and receipt["attempts"], "attempts are required")
    _require(len(receipt["attempts"]) <= 2, "too many attempts")

    for index, attempt in enumerate(receipt["attempts"], start=1):
        _validate_attempt(
            attempt,
            index,
            receipt["capability"],
            receipt["fallback_used"],
            receipt["parent_thread_id"],
            sessions_dir,
        )

    last = receipt["attempts"][-1]
    _require(receipt["state"] == last["state"], "lane state must match final attempt")
    if receipt["state"] == "SUCCEEDED":
        _require(receipt["verification"] == "VERIFIED", "successful lane must be verified")
    else:
        _require(receipt["verification"] == "NOT_VERIFIED", "failed lane is not verified")

    if receipt["fallback_used"] == "none":
        _require(len(receipt["attempts"]) == 1, "no-fallback lane must have one attempt")
    else:
        _require(receipt["capability"] == "fast", "only fast lane may use Spark fallback")
        _require(len(receipt["attempts"]) == 2, "Spark fallback requires two attempts")
        first, second = receipt["attempts"]
        _require(first["state"] == "FAILED", "first fallback attempt must fail")
        _require(first["cause"] == "model_unavailable", "fallback requires model_unavailable")
        _require(first["requested_model"] == "gpt-5.3-codex-spark", "first model must be Spark")
        _require(second["requested_model"] == "gpt-5.6-luna", "fallback model must be Luna")

    if receipt["capability"] == "frontier":
        _require(receipt["fallback_used"] == "none", "frontier lane cannot fallback")
        _require(
            receipt["attempts"][0]["requested_model"] == "gpt-5.6-sol",
            "frontier lane must request Sol",
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "route_id": receipt["route_id"],
        "lane": receipt["lane"],
        "state": receipt["state"],
        "verification": receipt["verification"],
    }


def derive_route_state(required_lane_states: list[str]) -> str:
    _require(bool(required_lane_states), "route requires at least one required lane")
    allowed = {"PENDING", "RUNNING", "SUCCEEDED", "FAILED"}
    _require(all(state in allowed for state in required_lane_states), "invalid lane state")
    if any(state in {"PENDING", "RUNNING"} for state in required_lane_states):
        return "RUNNING"
    succeeded = required_lane_states.count("SUCCEEDED")
    if succeeded == len(required_lane_states):
        return "SUCCEEDED"
    if succeeded == 0:
        return "FAILED"
    return "PARTIAL"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate one completed CCC lane receipt.")
    parser.add_argument("receipt", type=Path, help="Path to a receipt JSON file")
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=_default_sessions_dir(),
        help="Codex sessions directory used to bind child runtime evidence",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = json.loads(args.receipt.read_text(encoding="utf-8"))
        result = validate_receipt(payload, args.sessions_dir.expanduser())
    except (OSError, json.JSONDecodeError, ReceiptError):
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "code": "INVALID_RECEIPT",
                },
                sort_keys=True,
            )
        )
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "code": "INTERNAL_ERROR",
                },
                sort_keys=True,
            )
        )
        return 10

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
