from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any


INPUT_COLUMN_CANDIDATES = ["protein_accession_version", "accession", "protein_accession", "entry", "uniprot"]


def split_arg_values(values: list[str]) -> list[str]:
    items: list[str] = []
    for raw_value in values:
        for piece in raw_value.split(","):
            value = piece.strip()
            if value:
                items.append(value)
    return items


def _pick_first_value(row: dict[str, str], candidates: list[str]) -> str:
    lowered = {key.casefold(): value for key, value in row.items()}
    for candidate in candidates:
        value = lowered.get(candidate.casefold(), "").strip()
        if value:
            return value
    return ""


def load_accessions(*, accession_args: list[str], input_path: Path | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(value: str) -> None:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)

    for value in split_arg_values(accession_args):
        add(value)

    if input_path:
        if input_path.suffix.lower() == ".csv":
            with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    normalized = {str(key).strip(): str(value).strip() for key, value in row.items() if key is not None}
                    accession = _pick_first_value(normalized, INPUT_COLUMN_CANDIDATES)
                    if accession:
                        add(accession)
        else:
            for raw_line in input_path.read_text(encoding="utf-8-sig").splitlines():
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    for value in split_arg_values([line]):
                        add(value)

    return ordered


def copy_input_artifacts(*, input_path: Path | None, accessions: list[str], temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": "", "normalized_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    normalized_input_path = temp_dir / "normalized_input_accessions.txt"
    normalized_input_path.write_text("\n".join(accessions) + "\n", encoding="utf-8")
    metadata["normalized_input_file"] = str(normalized_input_path)
    if input_path:
        copied_input_path = temp_dir / f"original_input{input_path.suffix or '.txt'}"
        shutil.copyfile(input_path, copied_input_path)
        metadata["original_input_file"] = str(input_path)
        metadata["copied_input_file"] = str(copied_input_path)
    return metadata


def write_table(path: Path, fieldnames: list[str], rows: list[dict[str, Any]], *, delimiter: str = "\t") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
