#!/usr/bin/env python3
"""Validate committed CCC canary results against the public result schema."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANARY_DIR = ROOT / "evals" / "canary"
REQUESTED_MODELS = {None, "host-default", "gpt-5.3-codex-spark", "gpt-5.6-sol"}
RESOLVED_MODELS = {
    None,
    "gpt-5.3-codex-spark",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_fields(payload: dict, expected: dict) -> None:
    for key, value in expected.items():
        _require(payload.get(key) == value, f"invalid {payload.get('scenario_id')} field: {key}")


def validate_semantics(payload: dict) -> None:
    scenario = payload["scenario_id"]
    fixture_path = CANARY_DIR / "fixtures" / f"{scenario}.json"
    _require(fixture_path.is_file(), "canary fixture missing")
    _require(
        payload["fixture_sha256"] == hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "fixture digest mismatch",
    )
    _require(payload["requested_model"] in REQUESTED_MODELS, "invalid requested model")
    _require(payload["resolved_model"] in RESOLVED_MODELS, "invalid resolved model")
    _require(payload["worktree_unchanged"] is True, "canary changed the worktree")
    _require(payload["task_result"] == "PASS", "canary task did not pass")
    _require(
        payload["observed_child_count"] == payload["expected_child_count"],
        "child count mismatch",
    )

    if scenario == "solo-guard":
        _require_fields(
            payload,
            {
                "route": "solo",
                "expected_child_count": 0,
                "children_distinct": None,
                "requested_model": None,
                "resolved_model": None,
                "requested_effort": None,
                "resolved_effort": None,
                "fallback": "none",
                "failure_class": "none",
                "verification": "NOT_VERIFIED",
            },
        )
        return

    if scenario == "parallel-read":
        _require_fields(
            payload,
            {
                "route": "parallel-read",
                "expected_child_count": 2,
                "children_distinct": True,
                "requested_model": "host-default",
                "requested_effort": "host-default",
                "fallback": "none",
                "failure_class": "none",
                "verification": "VERIFIED",
            },
        )
        _require(payload["resolved_model"] is not None, "parallel model evidence missing")
        _require(payload["resolved_effort"] is not None, "parallel effort evidence missing")
        return

    if scenario == "fast-route-fallback":
        _require_fields(
            payload,
            {
                "route": "fast",
                "expected_child_count": 1,
                "children_distinct": None,
                "requested_model": "gpt-5.3-codex-spark",
                "requested_effort": "low",
                "resolved_effort": "low",
                "verification": "VERIFIED",
            },
        )
        if payload["fallback"] == "none":
            _require_fields(
                payload,
                {"resolved_model": "gpt-5.3-codex-spark", "failure_class": "none"},
            )
        else:
            _require_fields(payload, {"fallback": "spark_to_luna", "resolved_model": "gpt-5.6-luna"})
            _require(
                payload["failure_class"] in {"model_unavailable", "quota_denied"},
                "invalid fast fallback cause",
            )
        return

    if scenario == "host-default-judgment":
        _require_fields(
            payload,
            {
                "route": "standard",
                "expected_child_count": 1,
                "children_distinct": None,
                "requested_model": "host-default",
                "requested_effort": "host-default",
                "fallback": "none",
                "failure_class": "none",
                "verification": "VERIFIED",
            },
        )
        _require(payload["resolved_model"] is not None, "judgment model evidence missing")
        _require(payload["resolved_effort"] is not None, "judgment effort evidence missing")
        return

    if scenario == "frontier-seeded-defect-review":
        _require_fields(
            payload,
            {
                "route": "frontier",
                "expected_child_count": 1,
                "children_distinct": None,
                "requested_model": "gpt-5.6-sol",
                "resolved_model": "gpt-5.6-sol",
                "requested_effort": "high",
                "resolved_effort": "high",
                "fallback": "none",
                "failure_class": "none",
                "verification": "VERIFIED",
            },
        )
        return

    raise ValueError("unknown canary scenario")


def main() -> int:
    from jsonschema import Draft202012Validator

    schema = json.loads((CANARY_DIR / "result-schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    results = sorted((CANARY_DIR / "results").glob("*.json"))
    if not results:
        print("no canary results found", file=sys.stderr)
        return 2

    expected_scenarios = set(schema["properties"]["scenario_id"]["enum"])
    observed_scenarios = set()
    for path in results:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(payload)
        _require(payload["scenario_id"] not in observed_scenarios, "duplicate canary scenario")
        observed_scenarios.add(payload["scenario_id"])
        validate_semantics(payload)

    _require(observed_scenarios == expected_scenarios, "incomplete canary result set")

    print(f"validated {len(results)} canary results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
