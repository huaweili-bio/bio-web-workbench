from __future__ import annotations

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


def test_public_repo_keeps_only_runtime_code_and_public_docs() -> None:
    assert (ROOT / "README.md").exists()
    assert (ROOT / "requirements.txt").exists()
    assert (ROOT / "docs" / "TASKS.md").exists()
    assert WEBPAGES_ROOT.exists()
    assert not (ROOT / "scripts" / "protocol_gate.py").exists()


def test_public_repo_task_scripts_have_no_protocol_gate_references() -> None:
    assert iter_task_scripts()
    for path in iter_task_scripts():
        content = path.read_text(encoding="utf-8")
        assert "protocol_gate" not in content
        assert "validate_protocol_ticket" not in content
        assert "ProtocolGateError" not in content
        assert "--protocol-check-file" not in content
