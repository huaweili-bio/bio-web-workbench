from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path
from typing import Any
from urllib import parse

from .http_client import HttpClient, RemoteServiceError


DEFAULT_EFETCH_DOC = "https://www.ncbi.nlm.nih.gov/books/NBK25501/"
DEFAULT_EFETCH_ENDPOINT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
USER_AGENT = "bio-script-ncbi/1.0"
TRANSCRIPT_INPUT_COLUMN_CANDIDATES = [
    "transcript_accession_version",
    "transcript_accession",
    "transcript",
    "rna_accession",
    "accession",
]
FASTA_DETAIL_FIELDS = [
    "query_transcript_accession",
    "query_fasta_count",
    "query_gene_symbol",
    "gene_symbol",
    "transcript_accession_version",
    "transcript_accession",
    "fasta_header",
    "ncbi_fasta_header",
    "sequence_length",
]


class NcbiFastaError(RemoteServiceError):
    """Raised when NCBI EFetch returns an invalid response."""


class NcbiFastaClient:
    def __init__(self, *, timeout: float = 60.0, max_retries: int = 4) -> None:
        self._http = HttpClient(user_agent=USER_AGENT, timeout=timeout, max_retries=max_retries)

    def build_efetch_url(self, accession: str) -> str:
        params = [("db", "nuccore"), ("id", accession), ("rettype", "fasta"), ("retmode", "text")]
        return f"{DEFAULT_EFETCH_ENDPOINT}?{parse.urlencode(params)}"

    def fetch_fasta_text(self, accession: str) -> tuple[str, str]:
        url = self.build_efetch_url(accession)
        try:
            return url, self._http.read_text(url)
        except RemoteServiceError as exc:
            raise NcbiFastaError(str(exc)) from exc


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


def load_transcript_queries(*, transcript_args: list[str], input_path: Path | None) -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(accession: str, *, query_gene_symbol: str = "", gene_symbol: str = "") -> None:
        key = accession.casefold()
        if key in seen:
            return
        seen.add(key)
        ordered.append({"query_transcript_accession": accession, "query_gene_symbol": query_gene_symbol, "gene_symbol": gene_symbol or query_gene_symbol})

    for value in split_arg_values(transcript_args):
        add(value)

    if input_path:
        if input_path.suffix.lower() == ".csv":
            with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    normalized_row = {str(key).strip(): str(value).strip() for key, value in row.items() if key is not None}
                    accession = _pick_first_value(normalized_row, TRANSCRIPT_INPUT_COLUMN_CANDIDATES)
                    if accession:
                        query_gene_symbol = _pick_first_value(normalized_row, ["query_gene_symbol", "input_gene_symbol"])
                        gene_symbol = _pick_first_value(normalized_row, ["gene_symbol", "symbol", "gene"])
                        add(accession, query_gene_symbol=query_gene_symbol, gene_symbol=gene_symbol)
        else:
            for raw_line in input_path.read_text(encoding="utf-8-sig").splitlines():
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    for accession in split_arg_values([line]):
                        add(accession)

    return ordered


def copy_transcript_input_artifacts(*, input_path: Path | None, transcript_queries: list[dict[str, str]], temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": "", "normalized_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    normalized_input_path = temp_dir / "normalized_input_transcripts.csv"
    with normalized_input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query_transcript_accession", "query_gene_symbol", "gene_symbol"])
        writer.writeheader()
        writer.writerows(transcript_queries)
    metadata["normalized_input_file"] = str(normalized_input_path)
    if input_path:
        copied_input_path = temp_dir / f"original_input{input_path.suffix or '.txt'}"
        shutil.copyfile(input_path, copied_input_path)
        metadata["original_input_file"] = str(input_path)
        metadata["copied_input_file"] = str(copied_input_path)
    return metadata


def normalize_error_text(payload: str) -> str:
    text = " ".join(payload.split())
    return re.sub(r"\b([A-Za-z])(?:\s+([A-Za-z]))+\b", lambda match: match.group(0).replace(" ", ""), text)


def parse_fasta_response(payload: str) -> tuple[str, str, str]:
    stripped = payload.strip()
    if not stripped:
        raise NcbiFastaError("NCBI EFetch returned an empty response.")
    if stripped.startswith("Error:"):
        raise NcbiFastaError(normalize_error_text(stripped))
    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(">"):
        raise NcbiFastaError("NCBI EFetch did not return FASTA content.")
    header = lines[0][1:].strip()
    accession_version = header.split()[0]
    sequence = "".join(lines[1:]).replace(" ", "")
    if not sequence:
        raise NcbiFastaError("NCBI EFetch FASTA response does not contain sequence data.")
    return accession_version, header, sequence


def build_output_fasta_header(*, accession_version: str, query_gene_symbol: str, gene_symbol: str) -> str:
    parts = [accession_version]
    if gene_symbol:
        parts.append(f"gene_symbol={gene_symbol}")
    if query_gene_symbol:
        parts.append(f"query_gene_symbol={query_gene_symbol}")
    parts.append("source=NCBI")
    return " ".join(parts)


def build_fasta_summary_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_gene_symbol": str(row.get("query_gene_symbol") or ""),
        "gene_symbol": str(row.get("gene_symbol") or ""),
        "transcript_accession_version": str(row.get("transcript_accession_version") or ""),
        "sequence_length": int(row.get("sequence_length") or 0),
        "fasta_header": str(row.get("fasta_header") or ""),
    }
