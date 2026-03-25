#!/usr/bin/env python3
"""ENCORI task: query miRNA to lncRNA interactions."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any
from urllib import parse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.rnasysu_com.encori.common.http_text import RemoteServiceError, TextHttpClient
    from webpages.rnasysu_com.encori.common.io import (
        safe_filename,
        write_csv_rows,
        write_json,
        write_text,
    )
else:
    from ..common.http_text import RemoteServiceError, TextHttpClient
    from ..common.io import safe_filename, write_csv_rows, write_json, write_text

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_API_ENDPOINT = "https://rnasysu.com/encori/api/miRNATarget/"
DEFAULT_HOMEPAGE = "https://rnasysu.com/encori/"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "miRNA_lncRNA_ENCORI"
USER_AGENT = "bio-script-encori/1.0"
PAGE_KEY = "rnasysu_com.encori"
TASK_KEY = "mirna_to_lncrna"

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "miRNA",
    "bio_goal": "miRNA -> lncRNA targets",
    "provider": "ENCORI",
    "homepage": DEFAULT_HOMEPAGE,
    "api_endpoint": DEFAULT_API_ENDPOINT,
    "interaction_mode": "api",
    "master_file_mode": "direct_generated_master_file",
}
MASTER_FILE_NAME = "encori_result.csv"

class EncoriError(RemoteServiceError):
    """Raised when the ENCORI service returns an invalid response."""

class EncoriClient:
    """Client for the ENCORI miRNATarget endpoint."""

    def __init__(
        self,
        *,
        api_endpoint: str = DEFAULT_API_ENDPOINT,
        timeout: float = 60.0,
        max_retries: int = 4,
    ) -> None:
        self.api_endpoint = api_endpoint.rstrip("/") + "/"
        self._http = TextHttpClient(
            user_agent=USER_AGENT,
            timeout=timeout,
            max_retries=max_retries,
        )

    def build_request_url(
        self,
        mirna: str,
        *,
        assembly: str,
        clip_exp_num: int,
        degra_exp_num: int,
        pancancer_num: int,
        program_num: int,
        program: str,
        target: str,
        cell_type: str,
    ) -> str:
        params = [
            ("assembly", assembly),
            ("geneType", "lncRNA"),
            ("miRNA", mirna),
            ("clipExpNum", str(clip_exp_num)),
            ("degraExpNum", str(degra_exp_num)),
            ("pancancerNum", str(pancancer_num)),
            ("programNum", str(program_num)),
            ("program", program),
            ("target", target),
            ("cellType", cell_type),
        ]
        return f"{self.api_endpoint}?{parse.urlencode(params)}"

    def fetch_response_text(
        self,
        mirna: str,
        *,
        assembly: str,
        clip_exp_num: int,
        degra_exp_num: int,
        pancancer_num: int,
        program_num: int,
        program: str,
        target: str,
        cell_type: str,
    ) -> tuple[str, str]:
        url = self.build_request_url(
            mirna,
            assembly=assembly,
            clip_exp_num=clip_exp_num,
            degra_exp_num=degra_exp_num,
            pancancer_num=pancancer_num,
            program_num=program_num,
            program=program,
            target=target,
            cell_type=cell_type,
        )
        try:
            return url, self._http.read_text(url)
        except RemoteServiceError as exc:
            raise EncoriError(str(exc)) from exc

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch query ENCORI and export lncRNA hits for miRNAs.",
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
        "--assembly",
        choices=["hg38", "mm10"],
        default="hg38",
        help="Genome assembly used by ENCORI (default: hg38).",
    )
    parser.add_argument(
        "--clip-exp-num",
        type=int,
        default=1,
        help="Minimum number of supporting CLIP-seq experiments (default: 1).",
    )
    parser.add_argument(
        "--degra-exp-num",
        type=int,
        default=0,
        help="Minimum number of supporting degradome-seq experiments (default: 0).",
    )
    parser.add_argument(
        "--pancancer-num",
        type=int,
        default=0,
        help="Minimum number of supporting pan-cancer types (default: 0).",
    )
    parser.add_argument(
        "--program-num",
        type=int,
        default=1,
        help="Minimum number of target-predicting programs (default: 1).",
    )
    parser.add_argument(
        "--program",
        default="None",
        help="Predicting program filter, e.g. PITA, miRanda, or comma-separated values (default: None).",
    )
    parser.add_argument(
        "--target",
        default="all",
        help="Target gene name filter passed to ENCORI (default: all).",
    )
    parser.add_argument(
        "--cell-type",
        default="all",
        help="Cell type filter passed to ENCORI (default: all).",
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

def normalize_response_lines(payload: str) -> list[str]:
    return [
        line.rstrip("\r")
        for line in payload.splitlines()
        if line.strip() and not line.startswith("#")
    ]

def parse_response_table(payload: str) -> tuple[list[str], list[dict[str, str]], str | None]:
    lines = normalize_response_lines(payload)
    if not lines:
        raise EncoriError("ENCORI response does not contain a tab-delimited table.")

    reader = csv.reader(StringIO("\n".join(lines)), delimiter="\t")
    table = [[cell.strip() for cell in row] for row in reader]
    header = table[0]
    if not header:
        raise EncoriError("ENCORI response header is empty.")

    expected_columns = len(header)
    rows: list[dict[str, str]] = []
    error_messages: list[str] = []

    for row in table[1:]:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) == expected_columns:
            rows.append(dict(zip(header, row)))
            continue
        if len(row) == 1:
            error_messages.append(row[0])
            continue
        raise EncoriError(
            f"Malformed ENCORI row: expected {expected_columns} columns, got {len(row)}. Row: {row}"
        )

    if rows and error_messages:
        raise EncoriError("ENCORI response mixes data rows and error text.")

    error_message = "\n".join(error_messages).strip() or None
    return header, rows, error_message

def flatten_result_rows(
    query_mirna: str,
    response_header: list[str],
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        merged = {"query_mirna": query_mirna, "query_lncrna_count": 0}
        for column in response_header:
            merged[column] = row.get(column, "")
        flattened.append(merged)
    return flattened

def build_summary_entry(response_header: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    unique_lncrnas = sorted(
        {
            str(row.get("geneName") or "").strip()
            for row in rows
            if str(row.get("geneName") or "").strip()
        }
    )
    return {
        "lncrna_count": len(unique_lncrnas),
        "lncrnas": unique_lncrnas,
        "row_count": len(rows),
        "response_header": response_header,
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
    return DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{args.assembly}_{derive_job_name(args, mirnas)}"

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
        raise EncoriError("Use either --job-dir or --output-prefix, not both.")

    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "master_csv_path": args.output_prefix.with_suffix(".encori_result.csv"),
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
    except EncoriError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = EncoriClient(timeout=args.timeout)
    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    raw_dir = layout["raw_dir"]
    if isinstance(raw_dir, Path):
        raw_dir.mkdir(parents=True, exist_ok=True)

    input_artifacts = copy_input_artifacts(
        args=args,
        mirnas=mirnas,
        temp_dir=temp_dir,
    )

    fieldnames = ["query_mirna", "query_lncrna_count"]
    all_rows: list[dict[str, Any]] = []
    summary_entries: dict[str, Any] = {}
    failures: dict[str, str] = {}
    query_urls: dict[str, str] = {}

    for index, mirna in enumerate(mirnas, start=1):
        print(f"[{index}/{len(mirnas)}] Querying {mirna}", file=sys.stderr)
        try:
            query_url, payload = client.fetch_response_text(
                mirna,
                assembly=args.assembly,
                clip_exp_num=args.clip_exp_num,
                degra_exp_num=args.degra_exp_num,
                pancancer_num=args.pancancer_num,
                program_num=args.program_num,
                program=args.program,
                target=args.target,
                cell_type=args.cell_type,
            )
            query_urls[mirna] = query_url
        except EncoriError as exc:
            failures[mirna] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        if isinstance(raw_dir, Path):
            raw_path = raw_dir / f"{index:03d}_{safe_filename(mirna)}.tsv"
            write_text(raw_path, payload)

        try:
            response_header, rows, error_message = parse_response_table(payload)
        except EncoriError as exc:
            failures[mirna] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        if error_message:
            failures[mirna] = error_message
            print(f"  failed: {error_message}", file=sys.stderr)
            continue

        for column in response_header:
            if column not in fieldnames:
                fieldnames.append(column)

        flattened_rows = flatten_result_rows(mirna, response_header, rows)
        summary_entries[mirna] = build_summary_entry(response_header, rows)
        annotate_rows_with_query_count(flattened_rows, summary_entries[mirna]["lncrna_count"])
        all_rows.extend(flattened_rows)

        print(
            f"  {len(flattened_rows)} detailed rows, {summary_entries[mirna]['lncrna_count']} unique lncRNAs",
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

    write_csv_rows(master_csv_path, fieldnames, all_rows)
    write_json(
        summary_path,
        {
            "_meta": {
                "task": TASK_METADATA,
                "homepage": DEFAULT_HOMEPAGE,
                "api_endpoint": DEFAULT_API_ENDPOINT,
                "assembly": args.assembly,
                "clip_exp_num": args.clip_exp_num,
                "degra_exp_num": args.degra_exp_num,
                "pancancer_num": args.pancancer_num,
                "program_num": args.program_num,
                "program": args.program,
                "target": args.target,
                "cell_type": args.cell_type,
                "mirnas": mirnas,
                "output_mode": layout["mode"],
                "master_file_path": str(master_csv_path),
                "job_dir": str(layout["job_dir"]) if isinstance(layout["job_dir"], Path) else "",
                "temp_dir": str(layout["temp_dir"]) if isinstance(layout["temp_dir"], Path) else "",
                "raw_dir": str(raw_dir) if isinstance(raw_dir, Path) else "",
                "input_artifacts": input_artifacts,
                "query_urls": query_urls,
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
