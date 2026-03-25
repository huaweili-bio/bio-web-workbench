from __future__ import annotations

import csv
import html
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any
from urllib import parse, request


DEFAULT_HOME_URL = "https://cello.life.nctu.edu.tw/"
DEFAULT_SUBMIT_URL = "https://cello.life.nctu.edu.tw/cgi/main.cgi"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)
RESULT_FIELDS = ["sequence_id", "predicted_locations", "source_method", "species", "seqtype", "fasta_header"]


class CelloError(RuntimeError):
    """Raised when CELLO cannot be queried or parsed safely."""


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
        raise CelloError(f"No FASTA records were found in: {path}")
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


def normalize_sequence_for_seqtype(sequence: str, seqtype: str) -> str:
    normalized = "".join(sequence.split())
    if seqtype.lower() == "dna":
        # CELLO exposes a DNA mode. When users provide RNA/mRNA nucleotides,
        # normalize U to T before submitting to the DNA form.
        return normalized.upper().replace("U", "T")
    return normalized


def submit_query(*, fasta_record: dict[str, str], species: str, seqtype: str, timeout: float) -> str:
    normalized_sequence = normalize_sequence_for_seqtype(fasta_record["sequence"], seqtype)
    fasta_text = f">{fasta_record['fasta_header']}\n{normalized_sequence}"
    opener = request.build_opener(request.HTTPCookieProcessor())

    try:
        opener.open(
            request.Request(
                DEFAULT_HOME_URL,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,*/*",
                },
            ),
            timeout=timeout,
        ).read()
    except Exception:
        # The form POST itself is authoritative; a homepage warm-up is best effort only.
        pass

    payload = parse.urlencode(
        {
            "species": species,
            "seqtype": seqtype,
            "fasta": fasta_text,
            "Submit": "Submit",
        }
    ).encode("utf-8")

    def _request_with_payload(data: bytes, content_type: str) -> str:
        req = request.Request(
            DEFAULT_SUBMIT_URL,
            data=data,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": content_type,
                "Accept": "text/html,*/*",
                "Origin": "https://cello.life.nctu.edu.tw",
                "Referer": DEFAULT_HOME_URL,
            },
        )
        with opener.open(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    try:
        return _request_with_payload(payload, "application/x-www-form-urlencoded")
    except Exception as exc:
        first_error = exc

    boundary = f"----bio-script-{uuid.uuid4().hex}"
    multipart_lines = [
        f"--{boundary}",
        'Content-Disposition: form-data; name="species"',
        "",
        species,
        f"--{boundary}",
        'Content-Disposition: form-data; name="seqtype"',
        "",
        seqtype,
        f"--{boundary}",
        'Content-Disposition: form-data; name="Submit"',
        "",
        "Submit",
        f"--{boundary}",
        f'Content-Disposition: form-data; name="file"; filename="{fasta_record["sequence_id"]}.fasta"',
        "Content-Type: text/plain",
        "",
        fasta_text,
        f"--{boundary}--",
        "",
    ]
    multipart_payload = "\r\n".join(multipart_lines).encode("utf-8")
    try:
        return _request_with_payload(multipart_payload, f"multipart/form-data; boundary={boundary}")
    except Exception as exc:
        raise CelloError(
            f"Request failed for {DEFAULT_SUBMIT_URL}: form_post={first_error}; multipart_post={exc}"
        ) from exc


def _strip_html_tags(payload: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", payload, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _clean_cell_fragment(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text).replace("\xa0", " ")
    return " ".join(text.split()).strip(" .;:")


def parse_prediction_html(payload: str) -> list[str]:
    if "500 Internal Server Error" in payload:
        raise CelloError("CELLO returned HTTP 500 content.")
    if "The server encountered an internal error" in payload:
        raise CelloError("CELLO is currently unavailable and returned a server-side error page.")
    if "CELLO RESULTS" in payload and "CELLO Prediction:" in payload:
        prediction_section = payload.split("CELLO Prediction:", 1)[1]
        prediction_section = prediction_section.split("********************************************************************************", 1)[0]
        parsed_rows: list[tuple[str, str]] = []
        for location_html, score_html in re.findall(
            r"<tr>\s*<td>\s*&nbsp;\s*</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>",
            prediction_section,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            location = _clean_cell_fragment(location_html)
            score = _clean_cell_fragment(score_html)
            if location:
                parsed_rows.append((location, score))
        starred_predictions = [location for location, score in parsed_rows if "*" in score]
        if starred_predictions:
            return starred_predictions
        if parsed_rows:
            return [parsed_rows[0][0]]
    text = _strip_html_tags(payload)
    patterns = [
        r"predicted location\(s\)\s*[:\-]?\s*([A-Za-z ,;/.-]+)",
        r"prediction result\s*[:\-]?\s*([A-Za-z ,;/.-]+)",
        r"subcellular localization\s*[:\-]?\s*([A-Za-z ,;/.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).strip(" .;:")
            if raw:
                parts = [piece.strip(" .;:") for piece in re.split(r"[;,/]+", raw) if piece.strip(" .;:")]
                if parts:
                    return parts
    raise CelloError("Could not parse CELLO prediction output.")


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
