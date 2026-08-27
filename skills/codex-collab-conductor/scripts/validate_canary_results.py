#!/usr/bin/env python3
"""Validate committed CCC canary results against the public result schema."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANARY_DIR = ROOT / "evals" / "canary"
MODELS = {
    "gpt-5.3-codex-spark",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
}
CAPABILITY_ROUTES = {
    "fast": ("gpt-5.3-codex-spark", "low"),
    "bounded_implementation": ("gpt-5.6-luna", "max"),
    "standard": ("gpt-5.6-terra", "high"),
    "frontier": ("gpt-5.6-sol", "high"),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_fields(payload: dict, expected: dict) -> None:
    for key, value in expected.items():
        _require(payload.get(key) == value, f"invalid {payload.get('scenario_id')} field: {key}")


def _validate_lane_observation(
    payload: dict,
    observation: dict,
    route_policy: dict,
) -> None:
    capability = payload["capability_lane"]
    requested_model, requested_effort = CAPABILITY_ROUTES[capability]
    _require(observation["requested_model"] in MODELS, "invalid requested model")
    _require(
        observation["resolved_model"] is None or observation["resolved_model"] in MODELS,
        "invalid resolved model",
    )
    _require_fields(
        observation,
        {
            "requested_model": requested_model,
            "requested_effort": requested_effort,
        },
    )
    _require(
        observation["requested_model"] == route_policy["requested_model"],
        "lane request does not match fixture",
    )
    _require(
        observation["requested_effort"] == route_policy["requested_effort"],
        "lane effort does not match fixture",
    )

    if observation["fallback"] == "none":
        _require(observation["fallback_cause"] == "none", "no fallback cannot claim a cause")
        _require(
            not (
                capability == "fast"
                and observation["failure_class"] in {"model_unavailable", "quota_denied"}
            ),
            "eligible fast failure requires the permitted fallback",
        )
        if observation["resolved_model"] is not None:
            _require(
                observation["resolved_model"] == requested_model,
                "direct resolution must match the requested model",
            )
    else:
        _require(capability == "fast", "only fast capability may use Spark fallback")
        _require(
            observation["fallback_cause"] in {"model_unavailable", "quota_denied"},
            "invalid fast fallback cause",
        )
        if observation["resolved_model"] is not None:
            _require(
                observation["resolved_model"] == "gpt-5.6-luna",
                "fast fallback must resolve to Luna",
            )

    if observation["resolved_model"] is None:
        _require(observation["resolved_effort"] is None, "missing model cannot resolve effort")
        _require(
            observation["verification"] == "NOT_VERIFIED",
            "missing runtime model cannot be verified",
        )
    else:
        _require(
            observation["resolved_effort"] == requested_effort,
            "resolved effort must match the selected capability route",
        )

    if observation["verification"] == "VERIFIED":
        _require(observation["resolved_model"] is not None, "verified lane needs a resolved model")
    else:
        _require(
            observation["failure_class"] != "none",
            "unverified lane requires a final failure class",
        )
    if observation["failure_class"] in {"model_unavailable", "quota_denied", "capacity"}:
        _require(
            observation["resolved_model"] is None,
            "pre-child final failure cannot resolve a runtime model",
        )


def _validate_observation_consistency(payload: dict, route_policy: dict) -> None:
    observed_children = payload["observed_child_count"]
    if observed_children <= 1:
        _require(payload["children_distinct"] is None, "single-child result cannot claim distinctness")
    else:
        _require(isinstance(payload["children_distinct"], bool), "multi-child result needs distinctness")

    expected_lanes = route_policy["lanes"]
    observations = payload["lane_observations"]
    _require(
        [observation["lane"] for observation in observations] == expected_lanes,
        "lane observations do not match the fixture",
    )
    if payload["capability_lane"] is None:
        _require(observations == [], "solo route cannot record child lane observations")
        return
    _require(len(observations) == payload["expected_child_count"], "lane count mismatch")
    for observation in observations:
        _validate_lane_observation(payload, observation, route_policy)
    started_lanes = sum(
        observation["resolved_model"] is not None
        or observation["failure_class"] in {"timeout", "child_error", "evidence_missing"}
        for observation in observations
    )
    _require(
        started_lanes <= observed_children,
        "started lanes exceed observed child count",
    )


def validate_semantics(payload: dict) -> None:
    scenario = payload["scenario_id"]
    fixture_path = CANARY_DIR / "fixtures" / f"{scenario}.json"
    _require(fixture_path.is_file(), "canary fixture missing")
    _require(
        payload["fixture_sha256"] == hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "fixture digest mismatch",
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    _require(fixture["fixture_version"] == "ccc-native-canary-fixture-v2", "invalid fixture version")
    route_policy = fixture["route_policy"]
    _require_fields(
        payload,
        {
            "execution_route": route_policy["execution_route"],
            "capability_lane": route_policy["capability_lane"],
            "assurance_route": route_policy["assurance_route"],
            "expected_child_count": route_policy["expected_child_count"],
        },
    )
    _validate_observation_consistency(payload, route_policy)


def release_gate_failures(results: list[dict]) -> list[str]:
    failures: list[str] = []
    for payload in results:
        scenario = payload["scenario_id"]
        if payload["task_result"] != "PASS":
            failures.append(f"{scenario}: task_result={payload['task_result']}")
        if payload["worktree_unchanged"] is not True:
            failures.append(f"{scenario}: worktree_unchanged=false")
        if payload["observed_child_count"] != payload["expected_child_count"]:
            failures.append(
                f"{scenario}: child_count={payload['observed_child_count']}/"
                f"{payload['expected_child_count']}"
            )
        if payload["expected_child_count"] > 1 and payload["children_distinct"] is not True:
            distinct = str(payload["children_distinct"]).lower()
            failures.append(f"{scenario}: children_distinct={distinct}")
        for observation in payload["lane_observations"]:
            lane = observation["lane"]
            if observation["verification"] != "VERIFIED":
                failures.append(f"{scenario}/{lane}: verification={observation['verification']}")
            if observation["failure_class"] != "none":
                failures.append(f"{scenario}/{lane}: failure_class={observation['failure_class']}")
    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate committed CCC canary results.")
    parser.add_argument(
        "--release-gate",
        action="store_true",
        help="Fail when a valid observation set does not satisfy the release gate.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from jsonschema import Draft202012Validator

    args = _parser().parse_args(argv)
    schema = json.loads((CANARY_DIR / "result-schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    results = sorted((CANARY_DIR / "results").glob("*.json"))
    if not results:
        print("no canary results found", file=sys.stderr)
        return 2

    expected_scenarios = set(schema["properties"]["scenario_id"]["enum"])
    observed_scenarios = set()
    payloads: list[dict] = []
    for path in results:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(payload)
        _require(payload["scenario_id"] not in observed_scenarios, "duplicate canary scenario")
        observed_scenarios.add(payload["scenario_id"])
        validate_semantics(payload)
        payloads.append(payload)

    _require(observed_scenarios == expected_scenarios, "incomplete canary result set")

    print(f"validated {len(results)} canary results")
    if args.release_gate:
        failures = release_gate_failures(payloads)
        if failures:
            for failure in failures:
                print(f"release gate failed: {failure}", file=sys.stderr)
            return 1
        print("release gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
