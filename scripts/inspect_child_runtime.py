#!/usr/bin/env python3
"""Inspect one completed Codex child turn without exposing transcript content."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ccc-child-runtime-v1"
THREAD_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
AGENT_PATH_RE = re.compile(r"^/root(?:/[a-z0-9_-]+)+$")
KNOWN_MODELS = {
    "gpt-5.3-codex-spark",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-5.6-sol",
}
EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
OUTPUT_KEYS = {
    "schema_version",
    "status",
    "thread_id",
    "parent_thread_id",
    "turn_id",
    "completed",
    "depth",
    "model",
    "reasoning_effort",
}


class InspectorError(Exception):
    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def _default_sessions_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "sessions"
    return Path.home() / ".codex" / "sessions"


def _find_rollout(sessions_dir: Path, thread_id: str) -> Path:
    if not sessions_dir.is_dir():
        raise InspectorError(
            "INVALID_SESSIONS_DIR",
            "sessions directory does not exist or is not a directory",
            2,
        )

    suffix = f"-{thread_id}.jsonl"
    matches = sorted(
        path for path in sessions_dir.rglob(f"*{thread_id}.jsonl")
        if path.is_file() and path.name.endswith(suffix)
    )
    if not matches:
        raise InspectorError("NOT_FOUND", "no rollout matched the child thread id", 3)
    if len(matches) > 1:
        raise InspectorError(
            "MULTIPLE_MATCHES",
            f"more than one rollout matched the child thread id: {len(matches)}",
            4,
        )
    return matches[0]


def _nested(mapping: Any, *keys: str) -> Any:
    current = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _read_rollout(
    thread_id: str,
    sessions_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    if not THREAD_ID_RE.fullmatch(thread_id):
        raise InspectorError("INVALID_THREAD_ID", "invalid child thread id", 2)

    rollout = _find_rollout(sessions_dir, thread_id)
    session_meta: dict[str, Any] | None = None
    contexts: list[dict[str, Any]] = []
    completed_turns: set[str] = set()

    try:
        with rollout.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise InspectorError(
                        "MALFORMED_JSONL",
                        f"invalid JSON at line {line_number}: {error.msg}",
                        5,
                    ) from error

                if not isinstance(record, dict):
                    raise InspectorError(
                        "INVALID_JSONL_RECORD",
                        f"JSONL record is not an object at line {line_number}",
                        5,
                    )
                record_type = record.get("type")
                payload = record.get("payload")
                if record_type == "session_meta" and isinstance(payload, dict):
                    if payload.get("id") == thread_id:
                        if session_meta is not None:
                            raise InspectorError(
                                "DUPLICATE_SESSION_META",
                                "multiple matching session_meta records found",
                                5,
                            )
                        session_meta = payload
                elif record_type == "turn_context" and isinstance(payload, dict):
                    contexts.append(payload)
                elif (
                    record_type == "event_msg"
                    and isinstance(payload, dict)
                    and payload.get("type") == "task_complete"
                ):
                    completed_turn_id = payload.get("turn_id")
                    if isinstance(completed_turn_id, str) and THREAD_ID_RE.fullmatch(completed_turn_id):
                        completed_turns.add(completed_turn_id)
    except OSError as error:
        raise InspectorError("READ_FAILED", "failed to read rollout file", 5) from error

    if session_meta is None:
        raise InspectorError(
            "MISSING_SESSION_META",
            "matching session_meta record was not found",
            5,
        )
    return session_meta, contexts, completed_turns


def inspect_child_identity(thread_id: str, sessions_dir: Path) -> dict[str, Any]:
    session_meta, _, _ = _read_rollout(thread_id, sessions_dir)
    parent_thread_id = session_meta.get("parent_thread_id")
    agent_path = _nested(
        session_meta,
        "source",
        "subagent",
        "thread_spawn",
        "agent_path",
    )
    depth = _nested(
        session_meta,
        "source",
        "subagent",
        "thread_spawn",
        "depth",
    )
    if not isinstance(parent_thread_id, str) or not THREAD_ID_RE.fullmatch(parent_thread_id):
        raise InspectorError(
            "INVALID_RUNTIME_METADATA",
            "invalid runtime field: parent_thread_id",
            5,
        )
    if not isinstance(agent_path, str) or not AGENT_PATH_RE.fullmatch(agent_path):
        raise InspectorError(
            "INVALID_RUNTIME_METADATA",
            "invalid runtime field: agent_path",
            5,
        )
    if not isinstance(depth, int) or isinstance(depth, bool) or not 1 <= depth <= 16:
        raise InspectorError(
            "INVALID_RUNTIME_METADATA",
            "invalid runtime field: depth",
            5,
        )
    return {
        "thread_id": thread_id,
        "parent_thread_id": parent_thread_id,
        "depth": depth,
    }


def inspect_thread(
    thread_id: str,
    sessions_dir: Path,
    turn_id: str | None = None,
) -> dict[str, Any]:
    _, contexts, completed_turns = _read_rollout(thread_id, sessions_dir)
    if not contexts:
        raise InspectorError(
            "MISSING_TURN_CONTEXT",
            "turn_context record was not found",
            5,
        )

    context_by_turn: dict[str, list[dict[str, Any]]] = {}
    for context in contexts:
        context_turn_id = context.get("turn_id")
        if isinstance(context_turn_id, str) and THREAD_ID_RE.fullmatch(context_turn_id):
            context_by_turn.setdefault(context_turn_id, []).append(context)

    if turn_id is not None:
        if not THREAD_ID_RE.fullmatch(turn_id):
            raise InspectorError("INVALID_TURN_ID", "invalid turn id", 2)
        selected_turn_id = turn_id
    else:
        selectable = sorted(completed_turns.intersection(context_by_turn))
        if not selectable:
            raise InspectorError(
                "INCOMPLETE_CHILD_TURN",
                "no completed child turn with runtime context was found",
                5,
            )
        if len(selectable) > 1:
            raise InspectorError(
                "MULTIPLE_COMPLETED_TURNS",
                "multiple completed turns found; provide --turn-id",
                5,
            )
        selected_turn_id = selectable[0]

    result = inspect_turn_context(thread_id, sessions_dir, selected_turn_id)
    if not result["completed"]:
        raise InspectorError(
            "INCOMPLETE_CHILD_TURN",
            "selected child turn has no task_complete event",
            5,
        )
    return result


def inspect_turn_context(
    thread_id: str,
    sessions_dir: Path,
    turn_id: str,
) -> dict[str, Any]:
    if not THREAD_ID_RE.fullmatch(turn_id):
        raise InspectorError("INVALID_TURN_ID", "invalid turn id", 2)
    _, contexts, completed_turns = _read_rollout(thread_id, sessions_dir)
    identity = inspect_child_identity(thread_id, sessions_dir)
    selected_contexts = [
        context
        for context in contexts
        if context.get("turn_id") == turn_id
    ]
    if not selected_contexts:
        raise InspectorError(
            "MISSING_TURN_CONTEXT",
            "selected child turn has no runtime context",
            5,
        )

    models = {context.get("model") for context in selected_contexts}
    efforts = {context.get("effort") for context in selected_contexts}
    if len(models) != 1 or len(efforts) != 1:
        raise InspectorError(
            "CONFLICTING_RUNTIME_METADATA",
            "conflicting values found for selected child turn",
            5,
        )
    model = next(iter(models))
    reasoning_effort = next(iter(efforts))
    if not isinstance(model, str) or model not in KNOWN_MODELS:
        raise InspectorError(
            "INVALID_RUNTIME_METADATA",
            "invalid runtime field: model",
            5,
        )
    if not isinstance(reasoning_effort, str) or reasoning_effort not in EFFORTS:
        raise InspectorError(
            "INVALID_RUNTIME_METADATA",
            "invalid runtime field: reasoning_effort",
            5,
        )

    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "thread_id": thread_id,
        "parent_thread_id": identity["parent_thread_id"],
        "turn_id": turn_id,
        "completed": turn_id in completed_turns,
        "depth": identity["depth"],
        "model": model,
        "reasoning_effort": reasoning_effort,
    }
    if set(result) != OUTPUT_KEYS:
        raise InspectorError("INTERNAL_SCHEMA_ERROR", "invalid output schema", 10)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect allowlisted routing metadata for one completed Codex child turn."
    )
    parser.add_argument("thread_id", help="Exact child thread UUID")
    parser.add_argument("--turn-id", help="Exact completed child turn UUID")
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=_default_sessions_dir(),
        help="Codex sessions directory (defaults to CODEX_HOME/sessions)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = inspect_thread(
            args.thread_id,
            args.sessions_dir.expanduser(),
            args.turn_id,
        )
    except InspectorError as error:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "code": error.code,
                    "message": error.message,
                },
                sort_keys=True,
            )
        )
        return error.exit_code
    except Exception:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "code": "INTERNAL_ERROR",
                    "message": "unexpected inspector failure",
                },
                sort_keys=True,
            )
        )
        return 10

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
