from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inspect_child_runtime.py"
THREAD_ID = "01a032a6-4cdb-7de2-acae-2ee3a8f873fc"
PARENT_ID = "01a0319d-52b7-7853-8840-5ccd6bb436ff"
TURN_ID = "01a032a6-4e5b-7e73-ba5a-e555f9eec921"


def write_rollout(
    root: Path,
    thread_id: str = THREAD_ID,
    *,
    model: str = "gpt-5.3-codex-spark",
    effort: str = "low",
    sensitive: bool = False,
    completed: bool = True,
) -> Path:
    path = root / "2026" / "08" / "24" / f"rollout-test-{thread_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": thread_id,
                "parent_thread_id": PARENT_ID,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "agent_path": "/root/test_child",
                            "depth": 1,
                        }
                    }
                },
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "turn_id": TURN_ID,
                "model": model,
                "effort": effort,
                "sandbox_policy": {"type": "read-only"},
                "approval_policy": "never",
            },
        },
    ]
    if completed:
        records.append(
            {
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "turn_id": TURN_ID,
                    "last_agent_message": "SECRET_RESULT_SHOULD_NOT_APPEAR",
                },
            }
        )
    if sensitive:
        records.append(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "content": "SECRET_SHOULD_NOT_APPEAR",
                    "arguments": {"token": "ALSO_SECRET"},
                },
            }
        )
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def run_inspector(sessions_dir: Path, thread_id: str = THREAD_ID) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            thread_id,
            "--sessions-dir",
            str(sessions_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


class InspectorTests(unittest.TestCase):
    def test_success_returns_only_allowlisted_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_rollout(root, sensitive=True)
            result = run_inspector(root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["thread_id"], THREAD_ID)
        self.assertEqual(payload["parent_thread_id"], PARENT_ID)
        self.assertEqual(payload["turn_id"], TURN_ID)
        self.assertTrue(payload["completed"])
        self.assertEqual(payload["model"], "gpt-5.3-codex-spark")
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "status",
                "thread_id",
                "parent_thread_id",
                "turn_id",
                "completed",
                "depth",
                "model",
                "reasoning_effort",
            },
        )
        self.assertNotIn("SECRET_SHOULD_NOT_APPEAR", result.stdout)
        self.assertNotIn("ALSO_SECRET", result.stdout)
        self.assertNotIn("SECRET_RESULT_SHOULD_NOT_APPEAR", result.stdout)
        self.assertNotIn("content", payload)

    def test_invalid_thread_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_inspector(Path(directory), "not-a-thread-id")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["code"], "INVALID_THREAD_ID")

    def test_not_found_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_inspector(Path(directory))

        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["code"], "NOT_FOUND")

    def test_multiple_matches_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = write_rollout(root)
            second = root / "other" / first.name
            second.parent.mkdir(parents=True)
            second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
            result = run_inspector(root)

        self.assertEqual(result.returncode, 4)
        self.assertEqual(json.loads(result.stdout)["code"], "MULTIPLE_MATCHES")

    def test_conflicting_runtime_metadata_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_rollout(root)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "type": "turn_context",
                            "payload": {
                                "turn_id": TURN_ID,
                                "model": "gpt-5.6-luna",
                                "effort": "low",
                            },
                        }
                    )
                    + "\n"
                )
            result = run_inspector(root)

        self.assertEqual(result.returncode, 5)
        self.assertEqual(
            json.loads(result.stdout)["code"],
            "CONFLICTING_RUNTIME_METADATA",
        )

    def test_sensitive_value_in_allowlisted_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_rollout(root, model="PROMPT_SENTINEL")
            result = run_inspector(root)

        self.assertEqual(result.returncode, 5)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "INVALID_RUNTIME_METADATA")
        self.assertNotIn("PROMPT_SENTINEL", result.stdout)

    def test_model_shaped_sensitive_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_rollout(root, model="gpt-token-secret-abc123")
            result = run_inspector(root)

        self.assertEqual(result.returncode, 5)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "INVALID_RUNTIME_METADATA")
        self.assertNotIn("gpt-token-secret-abc123", result.stdout)

    def test_agent_path_is_never_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_rollout(root)
            content = path.read_text(encoding="utf-8").replace(
                "/root/test_child",
                "/root/token_secret_abc123",
            )
            path.write_text(content, encoding="utf-8")
            result = run_inspector(root)

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("agent_path", result.stdout)
        self.assertNotIn("token_secret_abc123", result.stdout)

    def test_non_object_json_record_fails_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_rollout(root)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("[]\n")
            result = run_inspector(root)

        self.assertEqual(result.returncode, 5)
        self.assertEqual(json.loads(result.stdout)["code"], "INVALID_JSONL_RECORD")
        self.assertEqual(result.stderr, "")

    def test_incomplete_child_turn_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_rollout(root, completed=False)
            result = run_inspector(root)

        self.assertEqual(result.returncode, 5)
        self.assertEqual(json.loads(result.stdout)["code"], "INCOMPLETE_CHILD_TURN")

    def test_malformed_json_fails_without_echoing_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_rollout(root)
            with path.open("a", encoding="utf-8") as handle:
                handle.write('{"secret":"DO_NOT_ECHO"\n')
            result = run_inspector(root)

        self.assertEqual(result.returncode, 5)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "MALFORMED_JSONL")
        self.assertNotIn("DO_NOT_ECHO", result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
