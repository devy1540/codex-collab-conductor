from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_review.py"


def run(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)


class PrepareReviewTests(unittest.TestCase):
    def make_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        run("git", "init", "-b", "main", cwd=repo)
        run("git", "config", "user.name", "Codex Test", cwd=repo)
        run("git", "config", "user.email", "codex@example.invalid", cwd=repo)
        (repo / "tracked.txt").write_text("before\n", encoding="utf-8")
        run("git", "add", "tracked.txt", cwd=repo)
        run("git", "commit", "-m", "initial", cwd=repo)
        return repo

    def test_working_tree_mode_tracks_untracked_blind_spot(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = self.make_repo(root)
            (repo / "tracked.txt").write_text("after\n", encoding="utf-8")
            (repo / "untracked.txt").write_text("not in patch\n", encoding="utf-8")
            artifact_root = root / "artifacts"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--working-tree",
                    "--workdir",
                    str(repo),
                    "--artifact-root",
                    str(artifact_root),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            output = json.loads(result.stdout)
            artifact_dir = Path(output["artifact_dir"])
            meta = json.loads((artifact_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["mode"], "working-tree")
            self.assertEqual(meta["untracked_files_count"], 1)
            self.assertFalse(meta["untracked_content_included"])
            self.assertIn("tracked.txt", (artifact_dir / "diff.patch").read_text(encoding="utf-8"))
            self.assertIn("untracked.txt", (artifact_dir / "untracked-files.txt").read_text(encoding="utf-8"))

    def test_artifact_directories_are_unique(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = self.make_repo(root)
            (repo / "tracked.txt").write_text("after\n", encoding="utf-8")
            artifact_root = root / "artifacts"
            paths = []
            for _ in range(2):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--working-tree",
                        "--workdir",
                        str(repo),
                        "--artifact-root",
                        str(artifact_root),
                    ],
                    text=True,
                    capture_output=True,
                    check=True,
                )
                paths.append(json.loads(result.stdout)["artifact_dir"])
            self.assertNotEqual(paths[0], paths[1])


if __name__ == "__main__":
    unittest.main()
