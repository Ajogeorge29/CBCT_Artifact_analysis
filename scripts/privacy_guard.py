"""Fail when private/raw research data is staged or tracked."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import PurePosixPath

PRIVATE_SUFFIXES = {
    ".dcm",
    ".dta",
    ".feather",
    ".mat",
    ".nii",
    ".nrrd",
    ".parquet",
    ".sav",
    ".xls",
    ".xlsb",
    ".xlsm",
    ".xlsx",
}


def _git_paths(arguments: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _reason(path_text: str) -> str | None:
    normalized = path_text.replace("\\", "/")
    path = PurePosixPath(normalized)
    lower_parts = tuple(part.lower() for part in path.parts)
    if len(lower_parts) >= 2 and lower_parts[:2] == ("data", "private"):
        if path.name != ".gitkeep":
            return "inside data/private"
    if path.suffix.lower() in PRIVATE_SUFFIXES:
        return f"raw/private extension {path.suffix.lower()}"
    if "master chart" in path.name.lower():
        return "private master-chart filename"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tracked", action="store_true", help="Inspect every tracked file")
    mode.add_argument("--staged", action="store_true", help="Inspect files staged for commit")
    args = parser.parse_args(argv)

    try:
        if args.tracked:
            paths = _git_paths(["ls-files", "-z"])
            label = "tracked"
        else:
            paths = _git_paths(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])
            label = "staged"
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"Privacy guard could not inspect Git: {error}", file=sys.stderr)
        return 2

    violations = [(path, reason) for path in paths if (reason := _reason(path))]
    if violations:
        print(f"Privacy guard blocked {len(violations)} {label} file(s):", file=sys.stderr)
        for path, reason in violations:
            print(f"  - {path}: {reason}", file=sys.stderr)
        return 1

    print(f"Privacy guard passed: {len(paths)} {label} file(s) inspected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
