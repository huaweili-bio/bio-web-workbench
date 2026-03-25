#!/usr/bin/env python3
"""Cell-PLoc 2.0 task: predict localization from human protein FASTA."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.csbio_sjtu_edu_cn.cell_ploc_2.common.core import CellPlocError, copy_input_artifacts, parse_fasta_records, parse_prediction_html, submit_query, write_csv_rows, write_json
else:
    from ..common.core import CellPlocError, copy_input_artifacts, parse_fasta_records, parse_prediction_html, submit_query, write_csv_rows, write_json

ROOT = Path(__file__).resolve().parents[5]
PAGE_KEY = "csbio_sjtu_edu_cn.cell_ploc_2"
TASK_KEY = "human_protein_fasta_to_localization"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "ProteinLoc_CellPLoc"

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit human protein FASTA records to Cell-PLoc 2.0 and parse localization predictions.")
    parser.add_argument("--input", type=Path, required=True, help="Input human protein FASTA file.")
    parser.add_argument("--job-dir", type=Path, help="Preferred output directory.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.input.exists():
        print(f"Input FASTA does not exist: {args.input}", file=sys.stderr)
        return 2

    try:
        fasta_records = parse_fasta_records(args.input)
    except CellPlocError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    job_dir = args.job_dir or (DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{args.input.stem}")
    temp_dir = job_dir / "temp"
    output_path = job_dir / "protein_localization_result.csv"
    raw_response_path = temp_dir / "raw_response.html"
    summary_path = temp_dir / "summary.json"
    errors_path = temp_dir / "errors.json"

    input_artifacts = copy_input_artifacts(input_path=args.input, temp_dir=temp_dir)
    rows: list[dict[str, str]] = []
    failures: dict[str, str] = {}
    raw_pages: list[str] = []
    for record in fasta_records:
        try:
            payload = submit_query(fasta_record=record, timeout=args.timeout)
            predicted = parse_prediction_html(payload)
        except CellPlocError as exc:
            failures[record["sequence_id"]] = str(exc)
            continue
        raw_pages.append(payload)
        rows.append(
            {
                "sequence_id": record["sequence_id"],
                "predicted_locations": ";".join(predicted),
                "source_method": "Cell-PLoc 2.0",
                "organism_model": "human_multi_label",
                "fasta_header": record["fasta_header"],
            }
        )

    query_success_count = len(fasta_records) - len(failures)
    result_status = "success"
    if failures and query_success_count > 0:
        result_status = "partial_success"
    elif failures:
        result_status = "failed"

    write_csv_rows(output_path, rows)
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_response_path.write_text("\n\n<!-- record break -->\n\n".join(raw_pages), encoding="utf-8")
    if failures:
        write_json(errors_path, failures)
    write_json(
        summary_path,
        {
            "_meta": {
                "page_key": PAGE_KEY,
                "task_key": TASK_KEY,
                "query_sequence_count": len(fasta_records),
                "query_success_count": query_success_count,
                "query_failure_count": len(failures),
                "matched_sequence_count": len(rows),
                "result_status": result_status,
                "job_dir": str(job_dir),
                "output_path": str(output_path),
                "raw_response_path": str(raw_response_path),
                "input_artifacts": input_artifacts,
            },
            "results": {row["sequence_id"]: row for row in rows},
        },
    )
    print(f"Result CSV: {output_path}", file=sys.stderr)
    print(f"Raw HTML: {raw_response_path}", file=sys.stderr)
    print(f"Summary JSON: {summary_path}", file=sys.stderr)
    if failures:
        print(f"Errors JSON: {errors_path}", file=sys.stderr)
    if result_status == "failed":
        print("Cell-PLoc failed for all sequences.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
