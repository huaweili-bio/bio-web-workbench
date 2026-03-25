#!/usr/bin/env python3
"""UniProtKB task: fetch subcellular localization annotation by protein accession."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from protocol_gate import ProtocolGateError, infer_input_type, validate_protocol_ticket
    from webpages.uniprot_org.uniprotkb.common.api import DEFAULT_API_DOC, UniProtClient, UniProtError, build_annotation_row
    from webpages.uniprot_org.uniprotkb.common.io import copy_input_artifacts, load_accessions, write_json, write_table
else:
    from protocol_gate import ProtocolGateError, infer_input_type, validate_protocol_ticket
    from ..common.api import DEFAULT_API_DOC, UniProtClient, UniProtError, build_annotation_row
    from ..common.io import copy_input_artifacts, load_accessions, write_json, write_table


ROOT = Path(__file__).resolve().parents[5]
PAGE_KEY = "uniprot_org.uniprotkb"
TASK_KEY = "protein_accession_to_localization_annotation"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "ProteinLoc_UniProtKB"
OUTPUT_FILENAME = "uniprot_subcellular_annotation.tsv"


def load_input_hints(input_path: Path | None) -> dict[str, dict[str, str]]:
    if input_path is None or input_path.suffix.lower() != ".csv" or not input_path.exists():
        return {}
    hints: dict[str, dict[str, str]] = {}
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            accession = str(
                row.get("protein_accession_version")
                or row.get("protein_accession")
                or row.get("accession")
                or ""
            ).strip()
            if not accession:
                continue
            hints[accession] = {
                "gene_symbol": str(row.get("gene_symbol") or row.get("query_gene_symbol") or "").strip(),
                "organism_id": str(row.get("tax_id") or "").strip(),
            }
    return hints


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch UniProtKB subcellular localization annotations for protein accessions.")
    parser.add_argument("--accession", action="append", default=[], help="Protein accession. Repeat the flag or pass comma-separated values.")
    parser.add_argument("--input", type=Path, help="Input file. Supports text or CSV.")
    parser.add_argument("--job-dir", type=Path, help="Preferred output directory.")
    parser.add_argument("--protocol-check-file", type=Path, help="Required protocol gate JSON for a formal run.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    accessions = load_accessions(accession_args=args.accession, input_path=args.input)
    if not accessions:
        print("No protein accessions were provided.", file=sys.stderr)
        return 2

    job_dir = args.job_dir or (DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{accessions[0]}")
    temp_dir = job_dir / "temp"
    output_path = job_dir / OUTPUT_FILENAME
    summary_path = temp_dir / "summary.json"
    errors_path = temp_dir / "errors.json"

    if args.protocol_check_file is None:
        print("Formal task execution requires --protocol-check-file. Generate it first via scripts/protocol_gate.py.", file=sys.stderr)
        return 2

    try:
        protocol_payload = validate_protocol_ticket(
            args.protocol_check_file,
            page_key=PAGE_KEY,
            task_key=TASK_KEY,
            input_type=infer_input_type(query_count=len(accessions), input_file=args.input),
            job_dir=job_dir,
        )
    except ProtocolGateError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.protocol_check_file.exists() and args.protocol_check_file.parent == job_dir:
        temp_dir.mkdir(parents=True, exist_ok=True)
        relocated_protocol = temp_dir / args.protocol_check_file.name
        if relocated_protocol.exists():
            relocated_protocol.unlink()
        shutil.move(str(args.protocol_check_file), str(relocated_protocol))
        args.protocol_check_file = relocated_protocol

    input_artifacts = copy_input_artifacts(input_path=args.input, accessions=accessions, temp_dir=temp_dir)
    client = UniProtClient(timeout=args.timeout)
    input_hints = load_input_hints(args.input)
    rows: list[dict[str, str]] = []
    failures: dict[str, str] = {}

    for accession in accessions:
        hint = input_hints.get(accession, {})
        try:
            source_url, payload_rows = client.fetch_annotation_rows(
                accession,
                gene_symbol=hint.get("gene_symbol", ""),
                organism_id=hint.get("organism_id", ""),
            )
        except UniProtError as exc:
            failures[accession] = str(exc)
            continue
        if not payload_rows:
            failures[accession] = "No UniProtKB entry matched the accession."
            continue
        rows.append(build_annotation_row(query_accession=accession, source_url=source_url, payload_row=payload_rows[0]))

    query_success_count = len(accessions) - len(failures)
    result_status = "success"
    if failures and query_success_count > 0:
        result_status = "partial_success"
    elif failures:
        result_status = "failed"

    fieldnames = [
        "query_accession",
        "entry",
        "entry_name",
        "gene_names",
        "protein_name",
        "annotation_score",
        "reviewed",
        "subcellular_location_text",
        "source_url",
    ]
    write_table(output_path, fieldnames, rows)
    if failures:
        write_json(errors_path, failures)
    write_json(
        summary_path,
        {
            "_meta": {
                "page_key": PAGE_KEY,
                "task_key": TASK_KEY,
                "api_doc": DEFAULT_API_DOC,
                "query_accession_count": len(accessions),
                "query_success_count": query_success_count,
                "query_failure_count": len(failures),
                "matched_accession_count": len(rows),
                "result_status": result_status,
                "job_dir": str(job_dir),
                "output_path": str(output_path),
                "protocol_check_file": str(args.protocol_check_file),
                "protocol_check": protocol_payload,
                "input_artifacts": input_artifacts,
            },
            "results": {row["query_accession"]: row for row in rows},
        },
    )
    print(f"Result TSV: {output_path}", file=sys.stderr)
    print(f"Summary JSON: {summary_path}", file=sys.stderr)
    if failures:
        print(f"Errors JSON: {errors_path}", file=sys.stderr)
    if result_status == "failed":
        print("UniProtKB failed for all accessions.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
