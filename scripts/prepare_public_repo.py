#!/usr/bin/env python3
"""Create a non-destructive public-safe export preview of this repository."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TOP_LEVEL_EXCLUDE_DIRS = {
    ".git",
    ".benchmarks",
    ".pytest_cache",
    ".pytest-basetemp",
    ".pytest_tmp",
    ".tmp",
    "outputs",
    "temp",
    "pytest_tmp_run",
}
EXCLUDE_DIR_NAMES = {"__pycache__", "local_data"}
EXCLUDE_SCRIPT_DOCS = {
    Path("scripts/AGENT_BRIEF.md"),
    Path("scripts/EXECUTION_PROTOCOL.md"),
    Path("scripts/START_HERE.md"),
    Path("scripts/TASK_INDEX.md"),
}
ALWAYS_INCLUDE = [
    Path(".gitignore"),
    Path("README.public.md"),
    Path("PUBLIC_REPO_SCOPE.md"),
    Path("data"),
    Path("docs"),
    Path("scripts/protocol_gate.py"),
    Path("scripts/merge_gene_mirna_lncrna_pairs.py"),
    Path("scripts/prepare_public_repo.py"),
    Path("scripts/webpages"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a public-safe export preview without deleting local working files."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Destination directory for the sanitized export preview.",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="Repository root. Defaults to the current repository.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests/ in the export preview.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output directory if it already exists.",
    )
    return parser.parse_args()


def should_skip(path: Path, source_root: Path, include_tests: bool) -> bool:
    relative = path.relative_to(source_root)

    if not relative.parts:
        return False
    if relative.parts[0] in TOP_LEVEL_EXCLUDE_DIRS:
        return True
    if relative.name in EXCLUDE_DIR_NAMES:
        return True
    if relative in EXCLUDE_SCRIPT_DOCS:
        return True
    if not include_tests and relative.parts[0] == "tests":
        return True
    return False


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".py", ".txt", ".json", ".csv", ".fasta"}


def rewrite_public_text(content: str, source_root: Path) -> str:
    replacements = [
        (str(source_root).replace("/", "\\") + "\\", ""),
        (str(source_root).replace("\\", "/") + "/", ""),
        (str(source_root).replace("/", "\\"), "."),
        (str(source_root).replace("\\", "/"), "."),
    ]
    rewritten = content
    for old, new in replacements:
        rewritten = rewritten.replace(old, new)
    return rewritten


def copy_path(source: Path, destination: Path, source_root: Path, include_tests: bool) -> None:
    if should_skip(source, source_root, include_tests):
        return

    if source.is_dir():
        for child in source.iterdir():
            if should_skip(child, source_root, include_tests):
                continue
            copy_path(child, destination / child.name, source_root, include_tests)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if is_text_file(source):
        content = source.read_text(encoding="utf-8")
        destination.write_text(rewrite_public_text(content, source_root), encoding="utf-8")
    else:
        shutil.copy2(source, destination)


def build_public_export(source_root: Path, output_dir: Path, include_tests: bool) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=False)

    for item in ALWAYS_INCLUDE:
        source = source_root / item
        if not source.exists():
            continue
        if item == Path("README.public.md"):
            destination = output_dir / "README.md"
            shutil.copy2(source, destination)
            continue
        copy_path(source, output_dir / item, source_root, include_tests)

    if include_tests:
        tests_dir = source_root / "tests"
        if tests_dir.exists():
            copy_path(tests_dir, output_dir / "tests", source_root, include_tests)


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root).resolve()
    output_dir = Path(args.output_dir).resolve()

    if args.force and output_dir.exists():
        shutil.rmtree(output_dir)

    build_public_export(source_root, output_dir, args.include_tests)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
