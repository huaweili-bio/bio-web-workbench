from __future__ import annotations

import csv
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib import parse, request


DEFAULT_SUBMIT_URL = "http://www.csbio.sjtu.edu.cn/cgi-bin/HummPLoc2.cgi"
USER_AGENT = "bio-script-cell-ploc/1.0"
RESULT_FIELDS = ["sequence_id", "predicted_locations", "source_method", "organism_model", "fasta_header"]


class CellPlocError(RuntimeError):
    """Raised when Cell-PLoc cannot be queried or parsed safely."""


def parse_fasta_records(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    header = ""
    chunks: list[str] = []

    def flush() -> None:
        nonlocal header, chunks
        if not header:
            return
        records.append(
            {
                "sequence_id": header.split()[0],
                "fasta_header": header,
                "sequence": "".join(chunks),
            }
        )
        header = ""
        chunks = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            flush()
            header = line[1:].strip()
        else:
            chunks.append(line)
    flush()
    if not records:
        raise CellPlocError(f"No FASTA records were found in: {path}")
    return records


def copy_input_artifacts(*, input_path: Path, temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": "", "normalized_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    copied_input = temp_dir / f"original_input{input_path.suffix or '.fa'}"
    normalized_input = temp_dir / "normalized_input.fasta"
    shutil.copyfile(input_path, copied_input)
    shutil.copyfile(input_path, normalized_input)
    metadata["original_input_file"] = str(input_path)
    metadata["copied_input_file"] = str(copied_input)
    metadata["normalized_input_file"] = str(normalized_input)
    return metadata


def submit_query(*, fasta_record: dict[str, str], timeout: float) -> str:
    payload = parse.urlencode(
        {
            "mode": "string",
            "S1": f">{fasta_record['fasta_header']}\n{fasta_record['sequence']}",
        }
    ).encode("utf-8")
    req = request.Request(
        DEFAULT_SUBMIT_URL,
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise CellPlocError(f"Request failed for {DEFAULT_SUBMIT_URL}: {exc}") from exc


def _strip_html_tags(payload: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", payload, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def parse_prediction_html(payload: str) -> list[str]:
    html_match = re.search(
        r"Predicted location\(s\)\s*</font>\s*</td>\s*</tr>\s*<tr[^>]*>\s*<td[^>]*>.*?</td>\s*<td[^>]*>.*?<font[^>]*>([^<]+)</font>",
        payload,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if html_match:
        raw = html.unescape(html_match.group(1)).strip(" .;:")
    else:
        text = _strip_html_tags(payload)
        match = re.search(r"Predicted location\(s\)\s+([A-Za-z .;-]+)", text, flags=re.IGNORECASE)
        if not match:
            raise CellPlocError("Could not parse Cell-PLoc prediction output.")
        raw = match.group(1).strip(" .;:")
    parts = [piece.strip(" .;:") for piece in re.split(r"[.;]+", raw) if piece.strip(" .;:")]
    if not parts:
        raise CellPlocError("Cell-PLoc prediction output did not contain localization labels.")
    return parts


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
