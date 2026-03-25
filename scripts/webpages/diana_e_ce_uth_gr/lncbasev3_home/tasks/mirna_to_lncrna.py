#!/usr/bin/env python3
"""DIANA-LncBase v3 task: query miRNA to lncRNA interactions."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib import parse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.diana_e_ce_uth_gr.lncbasev3_home.common.http_json import JsonHttpClient, RemoteServiceError
    from webpages.diana_e_ce_uth_gr.lncbasev3_home.common.io import safe_filename, write_csv_rows, write_json
else:
    from ..common.http_json import JsonHttpClient, RemoteServiceError
    from ..common.io import safe_filename, write_csv_rows, write_json

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SITE_BASE = "https://diana.e-ce.uth.gr"
DEFAULT_FALLBACK_API_BASE = "https://dianatest.e-ce.uth.gr/api"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "miRNA_lncRNA_LncBaseV3"
APP_CONFIG_PATH = "/assets/appConfig.json"
USER_AGENT = "bio-script-lncbasev3/1.0"
PAGE_KEY = "diana_e_ce_uth_gr.lncbasev3_home"
TASK_KEY = "mirna_to_lncrna"

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "miRNA",
    "bio_goal": "miRNA -> lncRNA targets",
    "provider": "DIANA-LncBase v3",
    "homepage": "https://diana.e-ce.uth.gr/lncbasev3/home",
    "interaction_mode": "api",
    "master_file_mode": "direct_generated_master_file",
}
MASTER_FILE_NAME = "lncbasev3_result.csv"

DETAIL_FIELDS = [
    "query_mirna",
    "query_lncrna_count",
    "result_mirna",
    "interaction_id",
    "gene_name",
    "external_gene_id",
    "external_transcript_id",
    "db_name",
    "biotype",
    "chromosome",
    "confidence_level",
    "predicted_score",
    "has_snps",
    "no_of_experiments",
    "no_of_publications",
    "no_of_cell_lines",
    "no_of_tissues",
    "no_of_high_throughput",
    "no_of_low_throughput",
    "expression_cell_type",
    "expression_tissue",
    "expression_category",
    "mirbase_link",
    "gene_ensembl_link",
]

class LncBaseError(RemoteServiceError):
    """Raised when the DIANA-LncBase service returns an invalid response."""

class LncBaseClient:
    """Client for DIANA-LncBase v3 API endpoints."""

    def __init__(
        self,
        *,
        site_base: str,
        api_base: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 4,
    ) -> None:
        self.site_base = site_base.rstrip("/")
        self.api_base = (api_base or "").rstrip("/")
        self._http = JsonHttpClient(
            user_agent=USER_AGENT,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _read_json(self, url: str) -> Any:
        try:
            return self._http.read_json(url)
        except RemoteServiceError as exc:
            raise LncBaseError(str(exc)) from exc

    def resolve_api_base(self) -> str:
        if self.api_base:
            return self.api_base

        config_url = f"{self.site_base}{APP_CONFIG_PATH}"
        try:
            config = self._read_json(config_url)
        except LncBaseError:
            self.api_base = DEFAULT_FALLBACK_API_BASE
            return self.api_base

        api_url = str(config.get("apiUrl") or "").strip().rstrip("/")
        self.api_base = api_url or DEFAULT_FALLBACK_API_BASE
        return self.api_base

    def fetch_options(self, endpoint: str) -> list[dict[str, Any]]:
        api_base = self.resolve_api_base()
        url = f"{api_base}/{endpoint.lstrip('/')}"
        payload = self._read_json(url)
        if not isinstance(payload, list):
            raise LncBaseError(f"Expected a list from {url}, got {type(payload).__name__}")
        return payload

    def resolve_named_options(
        self,
        endpoint: str,
        requested_values: list[str],
    ) -> list[dict[str, Any]]:
        if not requested_values:
            return []

        options = self.fetch_options(endpoint)
        resolved: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for raw_value in requested_values:
            value = raw_value.strip()
            if not value:
                continue

            exact_match = self._match_option(options, value)
            if exact_match is None:
                available = ", ".join(f"{item.get('key')}={item.get('value')}" for item in options)
                raise LncBaseError(
                    f"Unknown filter value '{value}' for {endpoint}. Available values: {available}"
                )

            key = str(exact_match.get("key"))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            resolved.append(exact_match)

        return resolved

    def _match_option(self, options: list[dict[str, Any]], value: str) -> dict[str, Any] | None:
        lowered = value.casefold()
        for option in options:
            if str(option.get("key")) == value:
                return option
            if str(option.get("value") or "").casefold() == lowered:
                return option

        partial_matches = [
            option
            for option in options
            if lowered in str(option.get("value") or "").casefold()
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]
        return None

    def fetch_result_payload(
        self,
        mirna: str,
        *,
        has_snps: str,
        species_keys: list[str],
        method_keys: list[str],
    ) -> dict[str, Any]:
        api_base = self.resolve_api_base()
        params: list[tuple[str, str]] = [("hasSnps", has_snps), ("mirnas", mirna)]
        params.extend(("species", key) for key in species_keys)
        params.extend(("methods", key) for key in method_keys)
        url = f"{api_base}/LncBaseV3/GetResult?{parse.urlencode(params, doseq=True)}"
        payload = self._read_json(url)
        if not isinstance(payload, dict):
            raise LncBaseError(f"Expected an object from {url}, got {type(payload).__name__}")
        return payload

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch query DIANA-LncBase v3 and export lncRNA hits for miRNAs.",
    )
    parser.add_argument(
        "--mirna",
        action="append",
        default=[],
        help="miRNA name. Repeat the flag or pass comma-separated values.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input file. Supports text or CSV. For CSV, a 'miRNA' column is preferred.",
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
        "--site-base",
        default=DEFAULT_SITE_BASE,
        help=f"Frontend site base used to discover appConfig.json (default: {DEFAULT_SITE_BASE}).",
    )
    parser.add_argument(
        "--api-base",
        help="Override the API base URL. If omitted, the script reads appConfig.json dynamically.",
    )
    parser.add_argument(
        "--species",
        action="append",
        default=[],
        help="Optional species filter by key or label, e.g. '1' or 'Homo sapiens'.",
    )
    parser.add_argument(
        "--method",
        action="append",
        default=[],
        help="Optional method filter by key or label, e.g. '9' or 'PAR-CLIP'.",
    )
    parser.add_argument(
        "--has-snps",
        default="All",
        help="Value passed through to hasSnps in the API query (default: All).",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional delay between API calls.",
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
        if "mirna" in header:
            index = header.index("mirna")
            start_row = 1

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

def load_mirnas(args: argparse.Namespace) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(value: str) -> None:
        if value not in seen:
            seen.add(value)
            ordered.append(value)

    for value in split_arg_values(args.mirna):
        add(value)

    if args.input:
        for value in load_values_from_input_file(args.input):
            add(value)

    return ordered

def flatten_result_rows(query_mirna: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue

        interaction_id = str(item.get("interactionId") or "")
        if interaction_id and interaction_id in seen_ids:
            continue
        if interaction_id:
            seen_ids.add(interaction_id)

        rows.append(
            {
                "query_mirna": query_mirna,
                "query_lncrna_count": 0,
                "result_mirna": item.get("mirnaName"),
                "interaction_id": item.get("interactionId"),
                "gene_name": item.get("geneName"),
                "external_gene_id": item.get("externalGeneId"),
                "external_transcript_id": item.get("externalTranscriptId"),
                "db_name": item.get("dbName"),
                "biotype": item.get("biotype"),
                "chromosome": item.get("chromosome"),
                "confidence_level": item.get("confidenceLevel"),
                "predicted_score": item.get("predictedScore"),
                "has_snps": item.get("hasSnps"),
                "no_of_experiments": item.get("noOfExperiments"),
                "no_of_publications": item.get("noOfPublications"),
                "no_of_cell_lines": item.get("noOfCellLines"),
                "no_of_tissues": item.get("noOfTissues"),
                "no_of_high_throughput": item.get("noOfHighThroughput"),
                "no_of_low_throughput": item.get("noOfLowThroughput"),
                "expression_cell_type": item.get("expressionCellType"),
                "expression_tissue": item.get("expressionTissue"),
                "expression_category": item.get("expressionCategory"),
                "mirbase_link": item.get("mirbaseLink"),
                "gene_ensembl_link": item.get("geneEnsemblLink"),
            }
        )

    rows.sort(
        key=lambda row: (
            str(row.get("query_mirna") or ""),
            str(row.get("gene_name") or ""),
            str(row.get("external_transcript_id") or ""),
        )
    )
    return rows

def build_summary_entry(payload: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    unique_lncrnas = sorted(
        {
            str(row.get("gene_name")).strip()
            for row in rows
            if row.get("gene_name") not in {None, ""}
        }
    )
    return {
        "lncrna_count": len(unique_lncrnas),
        "lncrnas": unique_lncrnas,
        "no_of_interactions": payload.get("noOfInteractions"),
        "no_of_publications": payload.get("noOfPublications"),
        "no_of_cell_lines": payload.get("noOfCellLines"),
        "no_of_tissues": payload.get("noOfTissues"),
        "methods": payload.get("methods", []),
    }

def annotate_rows_with_query_count(rows: list[dict[str, Any]], query_lncrna_count: int) -> None:
    for row in rows:
        row["query_lncrna_count"] = query_lncrna_count

def derive_job_name(args: argparse.Namespace, mirnas: list[str]) -> str:
    if args.job_name:
        return safe_filename(args.job_name)
    if args.input:
        return safe_filename(args.input.stem)
    if len(mirnas) == 1:
        return safe_filename(mirnas[0])
    return f"{safe_filename(mirnas[0])}_{len(mirnas)}_mirnas"

def resolve_job_dir(args: argparse.Namespace, mirnas: list[str]) -> Path:
    if args.job_dir:
        return args.job_dir
    return DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{derive_job_name(args, mirnas)}"

def copy_input_artifacts(
    *,
    args: argparse.Namespace,
    mirnas: list[str],
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
    normalized_input_path = temp_dir / "normalized_input_mirnas.txt"
    normalized_input_path.write_text("\n".join(mirnas) + "\n", encoding="utf-8")
    metadata["normalized_input_file"] = str(normalized_input_path)

    if args.input:
        copied_input_path = temp_dir / f"original_input{args.input.suffix or '.txt'}"
        shutil.copyfile(args.input, copied_input_path)
        metadata["original_input_file"] = str(args.input)
        metadata["copied_input_file"] = str(copied_input_path)
    return metadata

def build_output_layout(
    *,
    args: argparse.Namespace,
    mirnas: list[str],
) -> dict[str, Path | str | None]:
    if args.job_dir and args.output_prefix:
        raise LncBaseError("Use either --job-dir or --output-prefix, not both.")

    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "master_csv_path": args.output_prefix.with_suffix(".lncbasev3_result.csv"),
            "summary_path": args.output_prefix.with_suffix(".summary.json"),
            "errors_path": args.output_prefix.with_suffix(".errors.json"),
            "raw_dir": args.raw_dir,
        }

    job_dir = resolve_job_dir(args, mirnas)
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

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mirnas = load_mirnas(args)
    if not mirnas:
        print("No miRNA inputs were provided.", file=sys.stderr)
        return 2

    try:
        layout = build_output_layout(args=args, mirnas=mirnas)
    except LncBaseError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = LncBaseClient(
        site_base=args.site_base,
        api_base=args.api_base,
        timeout=args.timeout,
    )
    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    try:
        api_base = client.resolve_api_base()
        species_options = client.resolve_named_options(
            "LncBaseV3/GetMirnaSpeciesFilters",
            split_arg_values(args.species),
        )
        method_options = client.resolve_named_options(
            "LncBaseV3/GetMethodFilters",
            split_arg_values(args.method),
        )
    except LncBaseError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    raw_dir = layout["raw_dir"]
    if isinstance(raw_dir, Path):
        raw_dir.mkdir(parents=True, exist_ok=True)

    input_artifacts = copy_input_artifacts(
        args=args,
        mirnas=mirnas,
        temp_dir=temp_dir,
    )

    all_rows: list[dict[str, Any]] = []
    summary_entries: dict[str, Any] = {}
    failures: dict[str, str] = {}

    species_keys = [str(option["key"]) for option in species_options]
    method_keys = [str(option["key"]) for option in method_options]

    for index, mirna in enumerate(mirnas, start=1):
        print(f"[{index}/{len(mirnas)}] Querying {mirna}", file=sys.stderr)
        try:
            payload = client.fetch_result_payload(
                mirna,
                has_snps=args.has_snps,
                species_keys=species_keys,
                method_keys=method_keys,
            )
        except LncBaseError as exc:
            failures[mirna] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        rows = flatten_result_rows(mirna, payload)
        summary_entries[mirna] = build_summary_entry(payload, rows)
        annotate_rows_with_query_count(rows, summary_entries[mirna]["lncrna_count"])
        all_rows.extend(rows)

        if isinstance(raw_dir, Path):
            raw_path = raw_dir / f"{index:03d}_{safe_filename(mirna)}.json"
            write_json(raw_path, payload)

        print(
            f"  {len(rows)} detailed rows, {summary_entries[mirna]['lncrna_count']} unique lncRNAs",
            file=sys.stderr,
        )
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

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
                "site_base": args.site_base,
                "api_base": api_base,
                "mirnas": mirnas,
                "has_snps": args.has_snps,
                "species_filters": species_options,
                "method_filters": method_options,
                "output_mode": layout["mode"],
                "master_file_path": str(master_csv_path),
                "job_dir": str(layout["job_dir"]) if isinstance(layout["job_dir"], Path) else "",
                "temp_dir": str(layout["temp_dir"]) if isinstance(layout["temp_dir"], Path) else "",
                "raw_dir": str(raw_dir) if isinstance(raw_dir, Path) else "",
                "input_artifacts": input_artifacts,
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
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
