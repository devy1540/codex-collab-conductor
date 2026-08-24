#!/usr/bin/env python3
"""Validate a complete CCC route manifest and child independence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_lane_receipt import (  # noqa: E402
    ReceiptError,
    _default_sessions_dir,
    _valid_thread_id,
    derive_route_state,
    validate_receipt,
)


SCHEMA_VERSION = "ccc-route-manifest-v1"


class RouteError(Exception):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RouteError(message)


def _validate_basic(manifest: Any, sessions_dir: Path) -> dict[str, Any]:
    _require(isinstance(manifest, dict), "manifest must be an object")
    expected_keys = {
        "schema_version",
        "route_id",
        "supersedes_route_id",
        "replaces_lane",
        "parent_thread_id",
        "state",
        "required_lanes",
        "lanes",
    }
    _require(set(manifest) == expected_keys, "manifest keys do not match schema")
    _require(manifest["schema_version"] == SCHEMA_VERSION, "unsupported manifest schema")
    _require(_valid_thread_id(manifest["route_id"]), "invalid route id")
    _require(
        manifest["supersedes_route_id"] is None
        or _valid_thread_id(manifest["supersedes_route_id"]),
        "invalid superseded route id",
    )
    _require(manifest["supersedes_route_id"] != manifest["route_id"], "route cannot supersede itself")
    _require(
        manifest["replaces_lane"] is None or isinstance(manifest["replaces_lane"], str),
        "invalid replaced lane",
    )
    if manifest["supersedes_route_id"] is None:
        _require(manifest["replaces_lane"] is None, "initial route cannot replace a lane")
    else:
        _require(isinstance(manifest["replaces_lane"], str), "reroute requires replaced lane")
    _require(_valid_thread_id(manifest["parent_thread_id"]), "invalid parent thread id")
    _require(manifest["state"] in {"SUCCEEDED", "PARTIAL", "FAILED"}, "invalid completed route state")
    _require(
        isinstance(manifest["required_lanes"], list) and manifest["required_lanes"],
        "required lanes are required",
    )
    _require(
        all(isinstance(lane, str) for lane in manifest["required_lanes"]),
        "required lane names must be strings",
    )
    _require(
        len(set(manifest["required_lanes"])) == len(manifest["required_lanes"]),
        "required lane names must be unique",
    )
    _require(isinstance(manifest["lanes"], list) and manifest["lanes"], "lanes are required")

    lane_names: list[str] = []
    required_from_receipts: list[str] = []
    validated_lanes: list[dict[str, Any]] = []
    child_owner: dict[str, str] = {}
    seen_turns: set[tuple[str, str]] = set()

    for receipt in manifest["lanes"]:
        try:
            validated = validate_receipt(receipt, sessions_dir)
        except ReceiptError as error:
            raise RouteError("invalid lane receipt") from error
        _require(receipt["route_id"] == manifest["route_id"], "lane route id mismatch")
        _require(
            receipt["supersedes_route_id"] == manifest["supersedes_route_id"],
            "lane superseded route id mismatch",
        )
        _require(receipt["parent_thread_id"] == manifest["parent_thread_id"], "lane parent mismatch")
        lane_name = receipt["lane"]
        _require(lane_name not in lane_names, "lane names must be unique")
        lane_names.append(lane_name)
        if receipt["required"]:
            required_from_receipts.append(lane_name)
        validated_lanes.append(validated)

        for attempt in receipt["attempts"]:
            child_id = attempt["child_id"]
            turn_id = attempt["turn_id"]
            if child_id is None:
                continue
            previous_lane = child_owner.get(child_id)
            _require(
                previous_lane is None or previous_lane == lane_name,
                "one child cannot prove multiple lanes",
            )
            child_owner[child_id] = lane_name
            if turn_id is not None:
                key = (child_id, turn_id)
                _require(key not in seen_turns, "child turn cannot be reused")
                seen_turns.add(key)

    _require(set(lane_names) == {receipt["lane"] for receipt in manifest["lanes"]}, "lane mismatch")
    _require(
        set(required_from_receipts) == set(manifest["required_lanes"]),
        "required lane set mismatch",
    )
    required_states = [
        receipt["state"]
        for receipt in manifest["lanes"]
        if receipt["lane"] in manifest["required_lanes"]
    ]
    _require(
        derive_route_state(required_states) == manifest["state"],
        "route state does not match required lane states",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "route_id": manifest["route_id"],
        "state": manifest["state"],
        "required_lanes": sorted(manifest["required_lanes"]),
        "validated_lanes": sorted(lane["lane"] for lane in validated_lanes),
    }


def validate_route_manifest(
    manifest: Any,
    sessions_dir: Path,
    superseded_manifest: Any | None = None,
) -> dict[str, Any]:
    result = _validate_basic(manifest, sessions_dir)
    supersedes = manifest["supersedes_route_id"]
    if supersedes is None:
        _require(superseded_manifest is None, "unexpected superseded manifest")
        return result

    _require(superseded_manifest is not None, "superseded manifest is required")
    previous = _validate_basic(superseded_manifest, sessions_dir)
    _require(previous["route_id"] == supersedes, "superseded route id mismatch")
    _require(
        superseded_manifest["parent_thread_id"] == manifest["parent_thread_id"],
        "reroute parent mismatch",
    )
    _require(previous["state"] in {"PARTIAL", "FAILED"}, "superseded route must be terminal failure")
    replaced_lane = manifest["replaces_lane"]
    old_required = set(superseded_manifest["required_lanes"])
    new_required = set(manifest["required_lanes"])
    _require(replaced_lane in old_required, "replaced lane must be required by superseded route")
    old_replaced_receipts = [
        receipt for receipt in superseded_manifest["lanes"] if receipt["lane"] == replaced_lane
    ]
    _require(len(old_replaced_receipts) == 1, "replaced lane receipt is missing")
    old_replaced = old_replaced_receipts[0]
    _require(
        old_replaced["required"]
        and old_replaced["capability"] == "bounded_implementation"
        and old_replaced["state"] == "FAILED",
        "reroute requires a failed required bounded implementation lane",
    )

    retained_required = old_required - {replaced_lane}
    _require(
        retained_required.issubset(new_required),
        "reroute cannot drop other required lanes",
    )
    old_receipts_by_lane = {
        receipt["lane"]: receipt for receipt in superseded_manifest["lanes"]
    }
    new_receipts_by_lane = {
        receipt["lane"]: receipt for receipt in manifest["lanes"]
    }
    for lane_name in retained_required:
        _require(
            new_receipts_by_lane[lane_name]["capability"]
            == old_receipts_by_lane[lane_name]["capability"],
            "reroute cannot downgrade a retained required lane",
        )
    replacement_standard = any(
        receipt["required"]
        and receipt["capability"] == "standard"
        and (
            receipt["lane"] == replaced_lane
            or receipt["lane"] not in old_required
        )
        for receipt in manifest["lanes"]
    )
    _require(replacement_standard, "reroute requires a new replacement standard lane")

    previous_children = {
        attempt["child_id"]
        for receipt in superseded_manifest["lanes"]
        for attempt in receipt["attempts"]
        if attempt["child_id"] is not None
    }
    current_children = {
        attempt["child_id"]
        for receipt in manifest["lanes"]
        for attempt in receipt["attempts"]
        if attempt["child_id"] is not None
    }
    _require(
        previous_children.isdisjoint(current_children),
        "reroute lanes require fresh child evidence",
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a completed CCC route manifest.")
    parser.add_argument("manifest", type=Path, help="Path to route manifest JSON")
    parser.add_argument("--superseded-manifest", type=Path)
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
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        previous = (
            json.loads(args.superseded_manifest.read_text(encoding="utf-8"))
            if args.superseded_manifest
            else None
        )
        result = validate_route_manifest(
            manifest,
            args.sessions_dir.expanduser(),
            previous,
        )
    except (OSError, json.JSONDecodeError, ReceiptError, RouteError):
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "code": "INVALID_ROUTE_MANIFEST",
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
