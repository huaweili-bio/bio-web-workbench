from __future__ import annotations

import re
from typing import Any
from urllib import parse

from .http_client import HttpClient, RemoteServiceError


DEFAULT_EFETCH_DOC = "https://www.ncbi.nlm.nih.gov/books/NBK25501/"
DEFAULT_EFETCH_ENDPOINT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
USER_AGENT = "bio-script-ncbi-protein/1.0"
FASTA_DETAIL_FIELDS = [
    "query_gene_symbol",
    "gene_symbol",
    "transcript_accession_version",
    "protein_accession_version",
    "protein_accession",
    "protein_name",
    "fasta_header",
    "ncbi_fasta_header",
    "sequence_length",
]


class NcbiProteinFastaError(RemoteServiceError):
    """Raised when NCBI EFetch returns an invalid response."""


class NcbiProteinFastaClient:
    def __init__(self, *, timeout: float = 60.0, max_retries: int = 4) -> None:
        self._http = HttpClient(user_agent=USER_AGENT, timeout=timeout, max_retries=max_retries)

    def build_efetch_url(self, accession: str) -> str:
        params = [("db", "protein"), ("id", accession), ("rettype", "fasta"), ("retmode", "text")]
        return f"{DEFAULT_EFETCH_ENDPOINT}?{parse.urlencode(params)}"

    def fetch_fasta_text(self, accession: str) -> tuple[str, str]:
        url = self.build_efetch_url(accession)
        try:
            return url, self._http.read_text(url)
        except RemoteServiceError as exc:
            raise NcbiProteinFastaError(str(exc)) from exc


def normalize_error_text(payload: str) -> str:
    text = " ".join(payload.split())
    return re.sub(r"\b([A-Za-z])(?:\s+([A-Za-z]))+\b", lambda match: match.group(0).replace(" ", ""), text)


def parse_fasta_response(payload: str) -> tuple[str, str, str]:
    stripped = payload.strip()
    if not stripped:
        raise NcbiProteinFastaError("NCBI EFetch returned an empty response.")
    if stripped.startswith("Error:"):
        raise NcbiProteinFastaError(normalize_error_text(stripped))
    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(">"):
        raise NcbiProteinFastaError("NCBI EFetch did not return FASTA content.")
    header = lines[0][1:].strip()
    accession_version = header.split()[0]
    sequence = "".join(lines[1:]).replace(" ", "")
    if not sequence:
        raise NcbiProteinFastaError("NCBI EFetch FASTA response does not contain sequence data.")
    return accession_version, header, sequence


def build_output_fasta_header(*, accession_version: str, query_gene_symbol: str, gene_symbol: str, transcript_accession_version: str) -> str:
    parts = [accession_version]
    if gene_symbol:
        parts.append(f"gene_symbol={gene_symbol}")
    if query_gene_symbol:
        parts.append(f"query_gene_symbol={query_gene_symbol}")
    if transcript_accession_version:
        parts.append(f"transcript_accession_version={transcript_accession_version}")
    parts.append("source=NCBI")
    return " ".join(parts)


def build_fasta_summary_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_gene_symbol": str(row.get("query_gene_symbol") or ""),
        "gene_symbol": str(row.get("gene_symbol") or ""),
        "transcript_accession_version": str(row.get("transcript_accession_version") or ""),
        "protein_accession_version": str(row.get("protein_accession_version") or ""),
        "sequence_length": int(row.get("sequence_length") or 0),
        "fasta_header": str(row.get("fasta_header") or ""),
    }
