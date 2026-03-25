from __future__ import annotations

import csv
import html
import json
import ssl
import shutil
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib import parse, request


DEFAULT_SEARCH_URL = "http://www.rnalocate.org/show_search"
HTTPS_SEARCH_URL = "https://www.rnalocate.org/show_search"
USER_AGENT = "bio-script-rnalocate/1.0"
INPUT_COLUMN_CANDIDATES = ["rna", "rna_symbol", "symbol", "gene_symbol", "keyword"]
RESULT_FIELDS = [
    "query_rna_symbol",
    "rna_symbol",
    "category",
    "species",
    "localization",
    "sources",
    "pmid",
    "score",
]


class RNALocateError(RuntimeError):
    """Raised when RNALocate cannot be queried or parsed safely."""


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


def load_queries(*, rna_args: list[str], input_path: Path | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(value: str) -> None:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)

    for value in split_arg_values(rna_args):
        add(value)

    if input_path:
        if input_path.suffix.lower() == ".csv":
            with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    normalized = {str(key).strip(): str(value).strip() for key, value in row.items() if key is not None}
                    value = _pick_first_value(normalized, INPUT_COLUMN_CANDIDATES)
                    if value:
                        add(value)
        else:
            for raw_line in input_path.read_text(encoding="utf-8-sig").splitlines():
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    for value in split_arg_values([line]):
                        add(value)
    return ordered


def copy_input_artifacts(*, input_path: Path | None, queries: list[str], temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": "", "normalized_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    normalized_input_path = temp_dir / "normalized_input_rna_symbols.txt"
    normalized_input_path.write_text("\n".join(queries) + "\n", encoding="utf-8")
    metadata["normalized_input_file"] = str(normalized_input_path)
    if input_path:
        copied_input_path = temp_dir / f"original_input{input_path.suffix or '.txt'}"
        shutil.copyfile(input_path, copied_input_path)
        metadata["original_input_file"] = str(input_path)
        metadata["copied_input_file"] = str(copied_input_path)
    return metadata


def build_search_url(*, keyword: str, dataset: str, category: str, species: str, sources: str, search_type: str = "home") -> str:
    params: dict[str, str] = {
        "searchType": search_type,
        "dataset": dataset,
        "Keyword": keyword,
    }
    if category and category != "All":
        params["category"] = category
    if species and species != "All":
        params["species"] = species
    if sources and sources != "All":
        params["sources"] = sources
    return f"{DEFAULT_SEARCH_URL}?{parse.urlencode(params)}"


def fetch_search_html(*, url: str, timeout: float) -> str:
    req = request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        payload = ""
        if isinstance(exc, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc):
            fallback_url = url.replace(DEFAULT_SEARCH_URL, HTTPS_SEARCH_URL)
            try:
                with request.urlopen(
                    request.Request(fallback_url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"}),
                    timeout=timeout,
                    context=ssl._create_unverified_context(),
                ) as response:
                    payload = response.read().decode("utf-8", errors="replace")
            except Exception as inner_exc:
                raise RNALocateError(f"Request failed for {url}: {inner_exc}") from inner_exc
        else:
            raise RNALocateError(f"Request failed for {url}: {exc}") from exc
    if "Server Error (500)" in payload:
        if "searchType=exact" in url:
            fallback_url = url.replace("searchType=exact", "searchType=home")
            return fetch_search_html(url=fallback_url, timeout=timeout)
        raise RNALocateError(f"RNALocate returned HTTP 500 content for {url}.")
    return payload


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._current_row.append(" ".join("".join(self._current_cell).split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if any(cell.strip() for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._in_row = False
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(html.unescape(data))


def _normalize_header(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def parse_search_results(*, query_keyword: str, payload: str) -> list[dict[str, str]]:
    if "Invalid Request" in payload:
        raise RNALocateError("RNALocate returned Invalid Request.")
    parser = _TableParser()
    parser.feed(payload)
    selected_table: list[list[str]] | None = None
    for table in parser.tables:
        if not table:
            continue
        normalized_headers = {_normalize_header(value) for value in table[0]}
        if {"symbol", "localization"} <= normalized_headers or {"rnasymbol", "localization"} <= normalized_headers:
            selected_table = table
            break
    if selected_table is None:
        raise RNALocateError("Could not find a RNALocate result table in the response.")

    headers = [_normalize_header(value) for value in selected_table[0]]

    def get(row: list[str], *candidates: str) -> str:
        for candidate in candidates:
            normalized = _normalize_header(candidate)
            if normalized in headers:
                return row[headers.index(normalized)].strip()
        return ""

    rows: list[dict[str, str]] = []
    for row in selected_table[1:]:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        symbol = get(row, "RNA Symbol", "Symbol", "Gene Symbol")
        localization = get(row, "Localization", "Subcellular Localization")
        if not symbol and not localization:
            continue
        rows.append(
            {
                "query_rna_symbol": query_keyword,
                "rna_symbol": symbol,
                "category": get(row, "RNA Category", "Category"),
                "species": get(row, "Species", "Organism"),
                "localization": localization,
                "sources": get(row, "Source", "Sources", "Evidence"),
                "pmid": get(row, "PMID", "PubMed ID"),
                "score": get(row, "Score"),
            }
        )
    return rows


def write_table(path: Path, fieldnames: list[str], rows: list[dict[str, Any]], *, delimiter: str = "\t") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
