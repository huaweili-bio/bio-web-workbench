from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any
from urllib import parse

from .http_client import HttpClient, RemoteServiceError
from .io import safe_filename, write_text


DEFAULT_DATASETS_DOC = "https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/"
DEFAULT_PRODUCT_REPORT_ENDPOINT = "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol"
DEFAULT_TAXON = "Homo sapiens"
USER_AGENT = "bio-script-ncbi-protein/1.0"
INPUT_COLUMN_CANDIDATES = ["gene_symbol", "gene", "symbol", "mrna", "biomarker"]
PRODUCT_DETAIL_FIELDS = [
    "query_gene_symbol",
    "query_product_count",
    "gene_id",
    "gene_symbol",
    "gene_description",
    "tax_id",
    "taxname",
    "gene_type",
    "protein_rank",
    "protein_is_recommended",
    "transcript_accession_version",
    "transcript_accession",
    "transcript_name",
    "transcript_length",
    "transcript_type",
    "transcript_select_category",
    "protein_accession_version",
    "protein_accession",
    "protein_name",
    "protein_length",
]


class NcbiProteinError(RemoteServiceError):
    """Raised when the NCBI gene datasets service returns an invalid response."""


class NcbiProteinClient:
    def __init__(self, *, timeout: float = 60.0, max_retries: int = 4) -> None:
        self._http = HttpClient(user_agent=USER_AGENT, timeout=timeout, max_retries=max_retries)

    def build_product_report_url(self, gene_symbol: str, taxon: str) -> str:
        encoded_gene = parse.quote(gene_symbol, safe="")
        encoded_taxon = parse.quote(taxon, safe="")
        return f"{DEFAULT_PRODUCT_REPORT_ENDPOINT}/{encoded_gene}/taxon/{encoded_taxon}/product_report"

    def fetch_product_report(self, gene_symbol: str, taxon: str) -> tuple[str, dict[str, Any]]:
        url = self.build_product_report_url(gene_symbol, taxon)
        try:
            return url, self._http.read_json(url)
        except RemoteServiceError as exc:
            raise NcbiProteinError(str(exc)) from exc


def split_arg_values(values: list[str]) -> list[str]:
    items: list[str] = []
    for raw_value in values:
        for piece in raw_value.split(","):
            value = piece.strip()
            if value:
                items.append(value)
    return items


def load_values_from_input_file(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = [[cell.strip() for cell in row] for row in csv.reader(handle) if any(cell.strip() for cell in row)]
        if not rows:
            return []
        header = [cell.casefold() for cell in rows[0]]
        index = 0
        start_row = 0
        for candidate in INPUT_COLUMN_CANDIDATES:
            if candidate in header:
                index = header.index(candidate)
                start_row = 1
                break
        values: list[str] = []
        for row in rows[start_row:]:
            if index < len(row):
                values.extend(split_arg_values([row[index]]))
        return values

    values: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            values.extend(split_arg_values([line]))
    return values


def load_genes(*, gene_args: list[str], input_path: Path | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(value: str) -> None:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)

    for value in split_arg_values(gene_args):
        add(value)
    if input_path:
        for value in load_values_from_input_file(input_path):
            add(value)
    return ordered


def copy_gene_input_artifacts(*, input_path: Path | None, genes: list[str], temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": "", "normalized_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    normalized_input_path = temp_dir / "normalized_input_genes.txt"
    normalized_input_path.write_text("\n".join(genes) + "\n", encoding="utf-8")
    metadata["normalized_input_file"] = str(normalized_input_path)
    if input_path:
        copied_input_path = temp_dir / f"original_input{input_path.suffix or '.txt'}"
        shutil.copyfile(input_path, copied_input_path)
        metadata["original_input_file"] = str(input_path)
        metadata["copied_input_file"] = str(copied_input_path)
    return metadata


def _protein_accession_prefix_rank(accession_version: str) -> int:
    accession = accession_version.split(".", 1)[0].upper()
    if accession.startswith("NP_"):
        return 500
    if accession.startswith("XP_"):
        return 300
    return 100


def _select_category_rank(select_category: str) -> int:
    normalized = (select_category or "").upper()
    return {"MANE_SELECT": 1000, "MANE_PLUS_CLINICAL": 900, "REFSEQ_SELECT": 800}.get(normalized, 0)


def rank_protein_row(row: dict[str, Any]) -> tuple[Any, ...]:
    accession_version = str(row.get("protein_accession_version") or "")
    select_category = str(row.get("transcript_select_category") or "")
    protein_length = int(row.get("protein_length") or 0)
    return (-_select_category_rank(select_category), -_protein_accession_prefix_rank(accession_version), -protein_length, accession_version)


def _stringify(value: Any) -> str:
    return "" if value in {None, ""} else str(value)


def flatten_product_report(query_gene_symbol: str, product: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for transcript in product.get("transcripts", []):
        protein = transcript.get("protein") or {}
        accession_version = _stringify(protein.get("accession_version"))
        if not accession_version:
            continue
        transcript_accession_version = _stringify(transcript.get("accession_version"))
        rows.append(
            {
                "query_gene_symbol": query_gene_symbol,
                "query_product_count": 0,
                "gene_id": _stringify(product.get("gene_id")),
                "gene_symbol": _stringify(product.get("symbol")),
                "gene_description": _stringify(product.get("description")),
                "tax_id": _stringify(product.get("tax_id")),
                "taxname": _stringify(product.get("taxname")),
                "gene_type": _stringify(product.get("type")),
                "protein_rank": 0,
                "protein_is_recommended": 0,
                "transcript_accession_version": transcript_accession_version,
                "transcript_accession": transcript_accession_version.split(".", 1)[0] if transcript_accession_version else "",
                "transcript_name": _stringify(transcript.get("name")),
                "transcript_length": int(transcript.get("length") or 0),
                "transcript_type": _stringify(transcript.get("type")),
                "transcript_select_category": _stringify(transcript.get("select_category")),
                "protein_accession_version": accession_version,
                "protein_accession": accession_version.split(".", 1)[0],
                "protein_name": _stringify(protein.get("name")),
                "protein_length": int(protein.get("length") or 0),
            }
        )
    rows.sort(key=rank_protein_row)
    for index, row in enumerate(rows, start=1):
        row["protein_rank"] = index
        row["protein_is_recommended"] = 1 if index == 1 else 0
    return rows


def parse_product_report(payload: dict[str, Any], query_gene_symbol: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    reports = payload.get("reports")
    if not isinstance(reports, list) or not reports:
        return None, []
    report = reports[0]
    if not isinstance(report, dict):
        raise NcbiProteinError(f"NCBI product report for {query_gene_symbol} is malformed.")
    product = report.get("product")
    if not isinstance(product, dict):
        raise NcbiProteinError(f"NCBI product report for {query_gene_symbol} does not contain product details.")
    return product, flatten_product_report(query_gene_symbol, product)


def build_gene_summary_entry(product: dict[str, Any] | None, rows: list[dict[str, Any]]) -> dict[str, Any]:
    recommended_row = rows[0] if rows else {}
    return {
        "gene_id": _stringify((product or {}).get("gene_id")),
        "gene_symbol": _stringify((product or {}).get("symbol")),
        "gene_description": _stringify((product or {}).get("description")),
        "tax_id": _stringify((product or {}).get("tax_id")),
        "taxname": _stringify((product or {}).get("taxname")),
        "protein_count": len(rows),
        "recommended_protein_accession_version": _stringify(recommended_row.get("protein_accession_version")),
        "recommended_protein_accession": _stringify(recommended_row.get("protein_accession")),
        "recommended_select_category": _stringify(recommended_row.get("transcript_select_category")),
        "protein_accessions": [_stringify(row.get("protein_accession_version")) for row in rows if _stringify(row.get("protein_accession_version"))],
    }


def annotate_rows_with_query_count(rows: list[dict[str, Any]], query_product_count: int) -> None:
    for row in rows:
        row["query_product_count"] = query_product_count


def write_raw_gene_payload(*, raw_dir: Path | None, index: int, gene: str, payload: dict[str, Any]) -> None:
    if raw_dir is None:
        return
    raw_dir.mkdir(parents=True, exist_ok=True)
    write_text(raw_dir / f"{index:03d}_{safe_filename(gene)}.json", json.dumps(payload, ensure_ascii=False, indent=2))
