"""Output helpers local to the ENCORI webpage package."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Write dictionaries to CSV with a fixed field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with stable UTF-8 formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    """Write plain UTF-8 text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def safe_filename(value: str) -> str:
    """Normalize free text into a filesystem-safe leaf name."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "query"
