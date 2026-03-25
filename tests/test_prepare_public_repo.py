from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_public_repo.py"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_prepare_public_repo_sanitizes_docs_and_can_include_tests(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    out = tmp_path / "out"

    write_text(repo / ".gitignore", "outputs/\n")
    write_text(repo / "README.public.md", "# Public\n")
    write_text(repo / "PUBLIC_REPO_SCOPE.md", "# Scope\n")
    write_text(repo / "docs" / "QUICKSTART.md", "# Quickstart\n")
    write_text(repo / "data" / "protein_smoke.fasta", ">a\nAAAA\n")
    write_text(repo / "scripts" / "protocol_gate.py", "print('gate')\n")
    write_text(repo / "scripts" / "merge_gene_mirna_lncrna_pairs.py", "print('merge')\n")
    write_text(repo / "scripts" / "EXECUTION_PROTOCOL.md", "private\n")
    write_text(repo / "scripts" / "webpages" / "pkg" / "manifest.py", "PAGE = {}\n")
    write_text(
        repo / "scripts" / "webpages" / "pkg" / "README.md",
        f"see {repo.as_posix()}/scripts/webpages/pkg/README.md\n",
    )
    write_text(
        repo / "scripts" / "webpages" / "pkg" / "COMMANDS.md",
        f'python "{str(repo)}\\scripts\\protocol_gate.py"\n',
    )
    write_text(repo / "scripts" / "webpages" / "pkg" / "tasks" / "task.py", "print('ok')\n")
    write_text(repo / "scripts" / "webpages" / "pkg" / "__pycache__" / "junk.pyc", "x")
    write_text(repo / "scripts" / "webpages" / "targetscan_org" / "vert_80" / "local_data" / "big.zip", "x")
    write_text(repo / "tests" / "test_demo.py", "def test_ok(): pass\n")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(repo),
            "--output-dir",
            str(out),
            "--include-tests",
        ],
        check=True,
    )

    assert (out / "README.md").read_text(encoding="utf-8") == "# Public\n"
    assert (out / "PUBLIC_REPO_SCOPE.md").exists()
    assert (out / "docs" / "QUICKSTART.md").exists()
    assert (out / "data" / "protein_smoke.fasta").exists()
    assert (out / "scripts" / "protocol_gate.py").exists()
    assert (out / "scripts" / "webpages" / "pkg" / "manifest.py").exists()
    assert (out / "scripts" / "webpages" / "pkg" / "tasks" / "task.py").exists()
    assert (out / "tests" / "test_demo.py").exists()

    assert not (out / "scripts" / "EXECUTION_PROTOCOL.md").exists()
    assert not (out / "scripts" / "webpages" / "pkg" / "__pycache__").exists()
    assert not (out / "scripts" / "webpages" / "targetscan_org" / "vert_80" / "local_data").exists()

    assert (out / "scripts" / "webpages" / "pkg" / "README.md").read_text(encoding="utf-8") == "see scripts/webpages/pkg/README.md\n"
    assert (out / "scripts" / "webpages" / "pkg" / "COMMANDS.md").read_text(encoding="utf-8") == 'python "scripts\\protocol_gate.py"\n'
