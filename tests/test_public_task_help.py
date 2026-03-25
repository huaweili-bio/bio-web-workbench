from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEBPAGES_ROOT = ROOT / "scripts" / "webpages"

if (ROOT / "scripts" / "protocol_gate.py").exists():
    pytest.skip("Public webpage tests run only in the exported public repo.", allow_module_level=True)


def iter_task_scripts() -> list[Path]:
    return sorted(
        path
        for path in WEBPAGES_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
        and "local_data" not in path.parts
        and path.parent.name == "tasks"
        and path.name != "__init__.py"
    )


def test_each_public_task_script_exposes_help() -> None:
    for path in iter_task_scripts():
        completed = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, f"{path} failed with stderr: {completed.stderr}"
        assert "--protocol-check-file" not in completed.stdout
