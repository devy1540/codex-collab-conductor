#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CommandError(RuntimeError):
    pass


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        raise CommandError(f"command failed: {' '.join(cmd)}\n{stderr}")
    return result.stdout


def try_run(cmd: list[str], *, cwd: Path | None = None) -> str | None:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise CommandError(f"required tool not found on PATH: {name}")


def is_git_repo(workdir: Path) -> bool:
    return try_run(["git", "rev-parse", "--show-toplevel"], cwd=workdir) is not None


def git_top(workdir: Path) -> Path:
    output = run(["git", "rev-parse", "--show-toplevel"], cwd=workdir).strip()
    return Path(output)


def git_dir(workdir: Path) -> Path:
    output = run(["git", "rev-parse", "--git-dir"], cwd=workdir).strip()
    path = Path(output)
    if not path.is_absolute():
        path = workdir / path
    return path.resolve()


def ref_exists(workdir: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=str(workdir),
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def detect_base(workdir: Path) -> str:
    candidates: list[str] = []

    remote_head = try_run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=workdir)
    if remote_head:
        candidates.append(remote_head.strip().split("/")[-1])

    candidates.extend(["main", "master", "develop", "trunk"])

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if ref_exists(workdir, candidate):
            return candidate

    raise CommandError("could not detect a base branch; pass --base explicitly")


def parse_repo_slug(remote_url: str | None) -> str | None:
    if not remote_url:
        return None

    remote = remote_url.strip()
    if remote.startswith("git@github.com:"):
        slug = remote.split(":", 1)[1]
    elif "github.com/" in remote:
        slug = remote.split("github.com/", 1)[1]
    else:
        return None

    return slug.removesuffix(".git").strip("/") or None


def default_artifact_root(workdir: Path) -> Path:
    if is_git_repo(workdir):
        return git_dir(workdir) / "codex-review-pr"
    return Path(tempfile.gettempdir()) / "codex-review-pr"


def make_artifact_dir(root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    artifact_dir = root / f"review-pr-{timestamp}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    return artifact_dir


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_name_status(raw: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            rows.append({"status": status, "old_path": parts[1], "path": parts[2]})
        elif len(parts) >= 2:
            rows.append({"status": status, "path": parts[1]})
    return rows


def parse_numstat(raw: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        added, removed, _path = line.split("\t", 2)
        if added.isdigit():
            additions += int(added)
        if removed.isdigit():
            deletions += int(removed)
    return additions, deletions


def build_summary(meta: dict[str, Any], changed_files: list[str], artifact_dir: Path) -> str:
    lines = [
        "# Review Target",
        "",
        f"- Mode: {meta['mode']}",
        f"- Repository: {meta.get('repo') or 'unknown'}",
        f"- Base: {meta.get('base') or 'n/a'}",
        f"- Head: {meta.get('head') or 'n/a'}",
        f"- Changed files: {len(changed_files)}",
        f"- Additions: {meta.get('additions', 'n/a')}",
        f"- Deletions: {meta.get('deletions', 'n/a')}",
        f"- Untracked files: {meta.get('untracked_files_count', 0)}",
        f"- Untracked content in patch: {str(meta.get('untracked_content_included', True)).lower()}",
        f"- Empty diff: {str(meta['empty_diff']).lower()}",
        f"- Artifact dir: {artifact_dir}",
        "",
        "## Files",
    ]

    if changed_files:
        lines.extend(f"- {path}" for path in changed_files)
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def prepare_pr(args: argparse.Namespace, workdir: Path, artifact_dir: Path) -> dict[str, Any]:
    ensure_tool("gh")

    pr_ref = str(args.pr)
    repo_flag = ["--repo", args.repo] if args.repo else []

    meta_json = run(
        [
            "gh",
            "pr",
            "view",
            pr_ref,
            "--json",
            "number,title,url,baseRefName,headRefName,baseRefOid,headRefOid,mergeCommit,changedFiles,additions,deletions,isDraft,state,author,files,mergeStateStatus,reviewDecision,statusCheckRollup",
            *repo_flag,
        ],
        cwd=workdir,
    )
    meta = json.loads(meta_json)

    diff_patch = run(["gh", "pr", "diff", pr_ref, "--patch", *repo_flag], cwd=workdir)
    changed_files_raw = run(["gh", "pr", "diff", pr_ref, "--name-only", *repo_flag], cwd=workdir)
    changed_files = [line for line in changed_files_raw.splitlines() if line.strip()]
    diff_stat = "\n".join(
        f"{item.get('path', 'unknown')}\t+{item.get('additions', 0)}\t-{item.get('deletions', 0)}"
        for item in meta.get("files", [])
    )

    payload = {
        "mode": "pr",
        "repo": args.repo,
        "pr": meta["number"],
        "title": meta["title"],
        "url": meta["url"],
        "base": meta["baseRefName"],
        "head": meta["headRefName"],
        "base_sha": meta.get("baseRefOid"),
        "head_sha": meta.get("headRefOid"),
        "merge_commit": meta.get("mergeCommit"),
        "merge_state_status": meta.get("mergeStateStatus"),
        "review_decision": meta.get("reviewDecision"),
        "status_checks": meta.get("statusCheckRollup") or [],
        "additions": meta["additions"],
        "deletions": meta["deletions"],
        "changed_files_count": meta["changedFiles"],
        "empty_diff": not changed_files,
        "raw_meta": meta,
    }

    write_json(artifact_dir / "meta.json", payload)
    write_text(artifact_dir / "diff.patch", diff_patch)
    write_text(artifact_dir / "changed-files.txt", changed_files_raw)
    write_json(artifact_dir / "changed-files.json", {"files": meta.get("files", [])})
    write_text(artifact_dir / "diff-stat.txt", diff_stat + ("\n" if diff_stat else ""))
    write_text(artifact_dir / "summary.md", build_summary(payload, changed_files, artifact_dir))
    return payload


def prepare_git_diff(args: argparse.Namespace, workdir: Path, artifact_dir: Path) -> dict[str, Any]:
    ensure_tool("git")
    if not is_git_repo(workdir):
        raise CommandError("git diff mode requires running inside a git worktree")

    repo_root = git_top(workdir)
    base = args.base or detect_base(workdir)
    head = args.branch or args.head or "HEAD"
    compare_ref = f"{base}...{head}"

    diff_patch = run(["git", "diff", "--patch", "--binary", compare_ref], cwd=workdir)
    changed_files_raw = run(["git", "diff", "--name-only", compare_ref], cwd=workdir)
    diff_stat = run(["git", "diff", "--stat=200", compare_ref], cwd=workdir)
    numstat_raw = run(["git", "diff", "--numstat", compare_ref], cwd=workdir)
    name_status_raw = run(["git", "diff", "--name-status", compare_ref], cwd=workdir)
    changed_files = [line for line in changed_files_raw.splitlines() if line.strip()]
    additions, deletions = parse_numstat(numstat_raw)

    remote_url = try_run(["git", "remote", "get-url", "origin"], cwd=workdir)
    base_sha = run(["git", "rev-parse", base], cwd=workdir).strip()
    head_sha = run(["git", "rev-parse", head], cwd=workdir).strip()
    merge_base_sha = run(["git", "merge-base", base, head], cwd=workdir).strip()
    payload = {
        "mode": "branch" if args.branch else "current",
        "repo_root": str(repo_root),
        "repo": args.repo or parse_repo_slug(remote_url),
        "base": base,
        "head": head,
        "compare_ref": compare_ref,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "merge_base_sha": merge_base_sha,
        "additions": additions,
        "deletions": deletions,
        "empty_diff": not changed_files,
    }

    write_json(artifact_dir / "meta.json", payload)
    write_text(artifact_dir / "diff.patch", diff_patch)
    write_text(artifact_dir / "changed-files.txt", changed_files_raw)
    write_text(artifact_dir / "diff-stat.txt", diff_stat)
    write_json(artifact_dir / "changed-files.json", {"files": parse_name_status(name_status_raw)})
    write_text(artifact_dir / "summary.md", build_summary(payload, changed_files, artifact_dir))
    return payload


def prepare_working_tree(args: argparse.Namespace, workdir: Path, artifact_dir: Path) -> dict[str, Any]:
    ensure_tool("git")
    if not is_git_repo(workdir):
        raise CommandError("working-tree mode requires running inside a git worktree")

    repo_root = git_top(workdir)
    diff_patch = run(["git", "diff", "HEAD", "--patch", "--binary"], cwd=workdir)
    tracked_files_raw = run(["git", "diff", "HEAD", "--name-only"], cwd=workdir)
    untracked_files_raw = run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=workdir,
    )
    diff_stat = run(["git", "diff", "HEAD", "--stat=200"], cwd=workdir)
    numstat_raw = run(["git", "diff", "HEAD", "--numstat"], cwd=workdir)
    name_status_raw = run(["git", "diff", "HEAD", "--name-status"], cwd=workdir)
    tracked_files = [line for line in tracked_files_raw.splitlines() if line.strip()]
    untracked_files = [line for line in untracked_files_raw.splitlines() if line.strip()]
    changed_files = list(dict.fromkeys([*tracked_files, *untracked_files]))
    additions, deletions = parse_numstat(numstat_raw)
    remote_url = try_run(["git", "remote", "get-url", "origin"], cwd=workdir)
    head_sha = run(["git", "rev-parse", "HEAD"], cwd=workdir).strip()

    changed_file_rows = parse_name_status(name_status_raw)
    changed_file_rows.extend({"status": "?", "path": path} for path in untracked_files)
    payload = {
        "mode": "working-tree",
        "repo_root": str(repo_root),
        "repo": args.repo or parse_repo_slug(remote_url),
        "base": "HEAD",
        "head": "working-tree",
        "head_sha": head_sha,
        "additions": additions,
        "deletions": deletions,
        "untracked_files_count": len(untracked_files),
        "untracked_content_included": False,
        "empty_diff": not changed_files,
    }

    write_json(artifact_dir / "meta.json", payload)
    write_text(artifact_dir / "diff.patch", diff_patch)
    write_text(artifact_dir / "changed-files.txt", "\n".join(changed_files) + ("\n" if changed_files else ""))
    write_text(artifact_dir / "untracked-files.txt", untracked_files_raw)
    write_text(artifact_dir / "diff-stat.txt", diff_stat)
    write_json(artifact_dir / "changed-files.json", {"files": changed_file_rows})
    write_text(artifact_dir / "summary.md", build_summary(payload, changed_files, artifact_dir))
    return payload


def build_result(artifact_dir: Path, meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_dir": str(artifact_dir),
        "meta_path": str(artifact_dir / "meta.json"),
        "diff_path": str(artifact_dir / "diff.patch"),
        "changed_files_path": str(artifact_dir / "changed-files.txt"),
        "diff_stat_path": str(artifact_dir / "diff-stat.txt"),
        "summary_path": str(artifact_dir / "summary.md"),
        "untracked_files_path": str(artifact_dir / "untracked-files.txt")
        if (artifact_dir / "untracked-files.txt").exists()
        else None,
        "empty_diff": meta["empty_diff"],
        "mode": meta["mode"],
        "base": meta.get("base"),
        "head": meta.get("head"),
        "repo": meta.get("repo"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a PR, branch diff, or working tree for the review-pr skill.",
    )
    parser.add_argument("--pr", help="Pull request number, URL, or branch to fetch with gh")
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form for gh commands")
    parser.add_argument("--branch", help="Branch name to compare against --base")
    parser.add_argument("--head", help="Explicit git ref to compare against --base")
    parser.add_argument("--base", help="Base branch or git ref")
    parser.add_argument(
        "--working-tree",
        action="store_true",
        help="Review staged and unstaged tracked changes plus inventory untracked files",
    )
    parser.add_argument(
        "--artifact-root",
        help="Directory that will contain the generated review artifact directory",
    )
    parser.add_argument(
        "--workdir",
        default=".",
        help="Repository working directory. Defaults to the current directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(args.workdir).resolve()

    if args.pr and (args.branch or args.head or args.working_tree):
        raise CommandError("use exactly one of --pr, --working-tree, or git diff options")
    if args.working_tree and (args.branch or args.head or args.base):
        raise CommandError("--working-tree cannot be combined with --branch, --head, or --base")

    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else default_artifact_root(workdir)
    artifact_dir = make_artifact_dir(artifact_root)

    try:
        if args.pr:
            meta = prepare_pr(args, workdir, artifact_dir)
        elif args.working_tree:
            meta = prepare_working_tree(args, workdir, artifact_dir)
        else:
            meta = prepare_git_diff(args, workdir, artifact_dir)
    except Exception:
        shutil.rmtree(artifact_dir, ignore_errors=True)
        raise

    result = build_result(artifact_dir, meta)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if meta["empty_diff"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CommandError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
