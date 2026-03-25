#!/usr/bin/env python3
"""miRDB task: query mRNA biomarkers to mature miRNA predictions."""

from __future__ import annotations

import argparse
import csv
import html
import re
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib import parse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.mirdb_org.index.common.http_text import RemoteServiceError, TextHttpClient
    from webpages.mirdb_org.index.common.io import safe_filename, write_csv_rows, write_json, write_text
else:
    from ..common.http_text import RemoteServiceError, TextHttpClient
    from ..common.io import safe_filename, write_csv_rows, write_json, write_text

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_HOMEPAGE = "https://mirdb.org/"
DEFAULT_SEARCH_ENDPOINT = "https://mirdb.org/cgi-bin/search.cgi"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "mRNA_miRNA_miRDB"
USER_AGENT = "bio-script-mirdb/1.0"
PAGE_KEY = "mirdb_org.index"
TASK_KEY = "mrna_to_mirna"
INPUT_COLUMN_CANDIDATES = ["gene_symbol", "gene", "symbol", "mrna", "biomarker"]

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "mRNA",
    "bio_goal": "mRNA biomarker -> miRNA targets",
    "provider": "miRDB",
    "homepage": DEFAULT_HOMEPAGE,
    "search_endpoint": DEFAULT_SEARCH_ENDPOINT,
    "interaction_mode": "html_search",
    "master_file_mode": "direct_generated_master_file",
}
MASTER_FILE_NAME = "mirdb_result.csv"

DETAIL_FIELDS = [
    "query_gene_symbol",
    "query_mirna_count",
    "gene_id",
    "target_detail_id",
    "target_rank",
    "target_score",
    "mirna_name",
    "gene_symbol",
    "gene_description",
]

HIT_COUNT_PATTERN = re.compile(
    r"Gene\s+(?P<gene_id>\d+)\s+is\s+predicted\s+to\s+be\s+targeted\s+by\s+(?P<count>\d+)\s+miRNAs\s+in\s+miRDB",
    re.IGNORECASE,
)
NO_RESULT_PATTERN = re.compile(
    r'Warning:\s*no\s+Human\s+miRNA\s+is\s+predicted\s+to\s+target\s+symbol\s+"(?P<gene>[^"]+)"',
    re.IGNORECASE,
)
RESULT_TABLE_PATTERN = re.compile(
    r'<table[^>]*id="table1"[^>]*style="border-collapse:\s*collapse"[^>]*>(?P<table>.*?)</table>',
    re.IGNORECASE | re.DOTALL,
)
ROW_PATTERN = re.compile(r"<tr\b[^>]*>(?P<row>.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL_PATTERN = re.compile(r"<td\b[^>]*>(?P<cell>.*?)</td>", re.IGNORECASE | re.DOTALL)
TARGET_ID_PATTERN = re.compile(r"targetID=(?P<target_id>\d+)", re.IGNORECASE)

class MiRDBError(RemoteServiceError):
    """Raised when the miRDB website returns an invalid response."""

class MiRDBSearchClient:
    """Client for miRDB gene-symbol searches."""

    def __init__(
        self,
        *,
        search_endpoint: str = DEFAULT_SEARCH_ENDPOINT,
        timeout: float = 60.0,
        max_retries: int = 4,
    ) -> None:
        self.search_endpoint = search_endpoint
        self._http = TextHttpClient(
            user_agent=USER_AGENT,
            timeout=timeout,
            max_retries=max_retries,
        )

    def build_query_url(self, gene: str) -> str:
        params = [
            ("species", "Human"),
            ("geneChoice", "symbol"),
            ("searchBox", gene),
            ("searchType", "gene"),
        ]
        return f"{self.search_endpoint}?{parse.urlencode(params)}"

    def fetch_search_html(self, gene: str) -> tuple[str, str]:
        url = self.build_query_url(gene)
        try:
            return url, self._http.read_text(url)
        except RemoteServiceError as exc:
            raise MiRDBError(str(exc)) from exc

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch query miRDB and export mature miRNA hits for human gene symbols.",
    )
    parser.add_argument(
        "--gene",
        action="append",
        default=[],
        help="Gene symbol. Repeat the flag or pass comma-separated values.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input file. Supports text or CSV. For CSV, gene_symbol/gene/symbol/mrna/biomarker columns are preferred.",
    )
    parser.add_argument(
        "--job-dir",
        type=Path,
        help="Preferred output directory. Creates one clear task directory with final files and temp/.",
    )
    parser.add_argument(
        "--job-name",
        help="Optional label used to auto-build the job directory name.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        help="Legacy output prefix for <prefix>.details.csv and <prefix>.summary.json.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help="Optional raw response directory. In job-dir mode, a relative path is created under temp/.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args(argv)

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
            rows = [
                [cell.strip() for cell in row]
                for row in csv.reader(handle)
                if any(cell.strip() for cell in row)
            ]
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
            if index >= len(row):
                continue
            values.extend(split_arg_values([row[index]]))
        return values

    values: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        values.extend(split_arg_values([line]))
    return values

def load_genes(args: argparse.Namespace) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(value: str) -> None:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)

    for value in split_arg_values(args.gene):
        add(value)

    if args.input:
        for value in load_values_from_input_file(args.input):
            add(value)

    return ordered

def derive_job_name(args: argparse.Namespace, genes: list[str]) -> str:
    if args.job_name:
        return safe_filename(args.job_name)
    if args.input:
        return safe_filename(args.input.stem)
    if len(genes) == 1:
        return safe_filename(genes[0])
    return f"{safe_filename(genes[0])}_{len(genes)}_genes"

def resolve_job_dir(args: argparse.Namespace, genes: list[str]) -> Path:
    if args.job_dir:
        return args.job_dir
    return DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{derive_job_name(args, genes)}"

def build_output_layout(
    *,
    args: argparse.Namespace,
    genes: list[str],
) -> dict[str, Path | str | None]:
    if args.job_dir and args.output_prefix:
        raise MiRDBError("Use either --job-dir or --output-prefix, not both.")

    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "master_csv_path": args.output_prefix.with_suffix(".mirdb_result.csv"),
            "summary_path": args.output_prefix.with_suffix(".summary.json"),
            "errors_path": args.output_prefix.with_suffix(".errors.json"),
            "raw_dir": args.raw_dir,
        }

    job_dir = resolve_job_dir(args, genes)
    temp_dir = job_dir / "temp"
    raw_dir = args.raw_dir
    if raw_dir is not None and not raw_dir.is_absolute():
        raw_dir = temp_dir / raw_dir

    return {
        "mode": "job_dir",
        "job_dir": job_dir,
        "temp_dir": temp_dir,
        "master_csv_path": job_dir / MASTER_FILE_NAME,
        "summary_path": temp_dir / "summary.json",
        "errors_path": temp_dir / "errors.json",
        "raw_dir": raw_dir,
    }

def copy_input_artifacts(
    *,
    args: argparse.Namespace,
    genes: list[str],
    temp_dir: Path | None,
) -> dict[str, str]:
    metadata = {
        "original_input_file": "",
        "copied_input_file": "",
        "normalized_input_file": "",
    }
    if temp_dir is None:
        return metadata

    temp_dir.mkdir(parents=True, exist_ok=True)
    normalized_input_path = temp_dir / "normalized_input_genes.txt"
    normalized_input_path.write_text("\n".join(genes) + "\n", encoding="utf-8")
    metadata["normalized_input_file"] = str(normalized_input_path)

    if args.input:
        copied_input_path = temp_dir / f"original_input{args.input.suffix or '.txt'}"
        shutil.copyfile(args.input, copied_input_path)
        metadata["original_input_file"] = str(args.input)
        metadata["copied_input_file"] = str(copied_input_path)
    return metadata

def strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(text).split())

def parse_search_results(html_text: str) -> tuple[dict[str, Any], list[dict[str, str]], str | None]:
    hit_match = HIT_COUNT_PATTERN.search(html_text)
    if hit_match is None:
        no_result_match = NO_RESULT_PATTERN.search(html_text)
        if no_result_match is not None:
            query_gene = no_result_match.group("gene").strip()
            return {
                "gene_id": "",
                "reported_mirna_count": 0,
                "reported_query_gene": query_gene,
            }, [], f'No Human miRNA is predicted to target symbol "{query_gene}" in miRDB.'
        raise MiRDBError("miRDB response does not contain a recognized search result header.")

    metadata = {
        "gene_id": hit_match.group("gene_id").strip(),
        "reported_mirna_count": int(hit_match.group("count")),
        "reported_query_gene": "",
    }

    table_match = RESULT_TABLE_PATTERN.search(html_text)
    if table_match is None:
        raise MiRDBError("miRDB response does not contain the result table.")

    rows: list[dict[str, str]] = []
    for row_match in ROW_PATTERN.finditer(table_match.group("table")):
        row_html = row_match.group("row")
        cells = [cell_match.group("cell") for cell_match in CELL_PATTERN.finditer(row_html)]
        if len(cells) != 6:
            continue

        title = strip_tags(cells[0]).casefold()
        if "target detail" in title:
            continue

        target_id_match = TARGET_ID_PATTERN.search(cells[0])
        rows.append(
            {
                "gene_id": metadata["gene_id"],
                "target_detail_id": target_id_match.group("target_id").strip() if target_id_match else "",
                "target_rank": strip_tags(cells[1]),
                "target_score": strip_tags(cells[2]),
                "mirna_name": strip_tags(cells[3]),
                "gene_symbol": strip_tags(cells[4]),
                "gene_description": strip_tags(cells[5]),
            }
        )

    return metadata, rows, None

def flatten_result_rows(query_gene_symbol: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        flattened.append(
            {
                "query_gene_symbol": query_gene_symbol,
                "query_mirna_count": 0,
                "gene_id": row.get("gene_id", ""),
                "target_detail_id": row.get("target_detail_id", ""),
                "target_rank": row.get("target_rank", ""),
                "target_score": row.get("target_score", ""),
                "mirna_name": row.get("mirna_name", ""),
                "gene_symbol": row.get("gene_symbol", ""),
                "gene_description": row.get("gene_description", ""),
            }
        )
    return flattened

def build_summary_entry(metadata: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    unique_mirnas = sorted(
        {
            str(row.get("mirna_name") or "").strip()
            for row in rows
            if str(row.get("mirna_name") or "").strip()
        }
    )
    gene_symbols = sorted(
        {
            str(row.get("gene_symbol") or "").strip()
            for row in rows
            if str(row.get("gene_symbol") or "").strip()
        }
    )
    gene_descriptions = sorted(
        {
            str(row.get("gene_description") or "").strip()
            for row in rows
            if str(row.get("gene_description") or "").strip()
        }
    )
    return {
        "gene_id": metadata.get("gene_id", ""),
        "reported_mirna_count": int(metadata.get("reported_mirna_count", 0) or 0),
        "mirna_count": len(unique_mirnas),
        "mirnas": unique_mirnas,
        "row_count": len(rows),
        "gene_symbols": gene_symbols,
        "gene_descriptions": gene_descriptions,
    }

def annotate_rows_with_query_count(rows: list[dict[str, Any]], query_mirna_count: int) -> None:
    for row in rows:
        row["query_mirna_count"] = query_mirna_count

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    genes = load_genes(args)
    if not genes:
        print("No gene inputs were provided.", file=sys.stderr)
        return 2

    try:
        layout = build_output_layout(args=args, genes=genes)
    except MiRDBError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = MiRDBSearchClient(timeout=args.timeout)
    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    raw_dir = layout["raw_dir"]
    if isinstance(raw_dir, Path):
        raw_dir.mkdir(parents=True, exist_ok=True)

    input_artifacts = copy_input_artifacts(
        args=args,
        genes=genes,
        temp_dir=temp_dir,
    )

    all_rows: list[dict[str, Any]] = []
    summary_entries: dict[str, Any] = {}
    failures: dict[str, str] = {}
    query_urls: dict[str, str] = {}
    unmatched_query_genes: list[str] = []

    for index, gene in enumerate(genes, start=1):
        print(f"[{index}/{len(genes)}] Querying {gene}", file=sys.stderr)
        try:
            query_url, html_text = client.fetch_search_html(gene)
            query_urls[gene] = query_url
        except MiRDBError as exc:
            failures[gene] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        if isinstance(raw_dir, Path):
            raw_path = raw_dir / f"{index:03d}_{safe_filename(gene)}.html"
            write_text(raw_path, html_text)

        try:
            response_meta, rows, no_hit_message = parse_search_results(html_text)
        except MiRDBError as exc:
            failures[gene] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        summary_entry = build_summary_entry(response_meta, rows)
        summary_entries[gene] = summary_entry
        flattened_rows = flatten_result_rows(gene, rows)
        annotate_rows_with_query_count(flattened_rows, summary_entry["mirna_count"])
        all_rows.extend(flattened_rows)

        if no_hit_message:
            unmatched_query_genes.append(gene)
            failures[gene] = no_hit_message
            print(f"  no hit: {no_hit_message}", file=sys.stderr)
            continue

        print(
            f"  {summary_entry['mirna_count']} unique miRNAs, {summary_entry['row_count']} detailed rows",
            file=sys.stderr,
        )

    all_rows.sort(
        key=lambda row: (
            str(row.get("query_gene_symbol") or ""),
            int(str(row.get("target_rank") or "999999")),
            str(row.get("mirna_name") or ""),
        )
    )

    master_csv_path = layout["master_csv_path"]
    summary_path = layout["summary_path"]
    errors_path = layout["errors_path"]
    assert isinstance(master_csv_path, Path)
    assert isinstance(summary_path, Path)
    assert isinstance(errors_path, Path)

    write_csv_rows(master_csv_path, DETAIL_FIELDS, all_rows)
    write_json(
        summary_path,
        {
            "_meta": {
                "task": TASK_METADATA,
                "homepage": DEFAULT_HOMEPAGE,
                "search_endpoint": DEFAULT_SEARCH_ENDPOINT,
                "query_genes": genes,
                "output_mode": layout["mode"],
                "master_file_path": str(master_csv_path),
                "job_dir": str(layout["job_dir"]) if isinstance(layout["job_dir"], Path) else "",
                "temp_dir": str(layout["temp_dir"]) if isinstance(layout["temp_dir"], Path) else "",
                "raw_dir": str(raw_dir) if isinstance(raw_dir, Path) else "",
                "input_artifacts": input_artifacts,
                "query_urls": query_urls,
                "unmatched_query_genes": unmatched_query_genes,
                "master_file_generation": "direct_generated_master_file",
                "master_file_is_concatenated": False,
            },
            "results": summary_entries,
        },
    )

    if failures:
        write_json(errors_path, failures)

    print(f"Master CSV: {master_csv_path}", file=sys.stderr)
    if failures:
        print(f"Errors JSON: {errors_path}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
