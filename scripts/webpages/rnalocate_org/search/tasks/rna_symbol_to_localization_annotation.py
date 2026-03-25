#!/usr/bin/env python3
"""RNALocate task: fetch localization annotation by RNA symbol."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from protocol_gate import ProtocolGateError, infer_input_type, validate_protocol_ticket
    from webpages.rnalocate_org.search.common.core import RESULT_FIELDS, RNALocateError, build_search_url, copy_input_artifacts, fetch_search_html, load_queries, parse_search_results, write_json, write_table
else:
    from protocol_gate import ProtocolGateError, infer_input_type, validate_protocol_ticket
    from ..common.core import RESULT_FIELDS, RNALocateError, build_search_url, copy_input_artifacts, fetch_search_html, load_queries, parse_search_results, write_json, write_table


ROOT = Path(__file__).resolve().parents[5]
PAGE_KEY = "rnalocate_org.search"
TASK_KEY = "rna_symbol_to_localization_annotation"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "RNALoc_RNALocate"
OUTPUT_FILENAME = "rnalocate_localization_annotation.tsv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch RNALocate localization annotations for RNA symbols.")
    parser.add_argument("--rna", action="append", default=[], help="RNA symbol. Repeat the flag or pass comma-separated values.")
    parser.add_argument("--input", type=Path, help="Input file. Supports text or CSV.")
    parser.add_argument("--job-dir", type=Path, help="Preferred output directory.")
    parser.add_argument("--dataset", default="Symbol", help='RNALocate dataset field. Default: "Symbol".')
    parser.add_argument("--category", default="All", help='RNALocate category filter. Default: "All".')
    parser.add_argument("--species", default="All", help='RNALocate species filter. Default: "All".')
    parser.add_argument("--sources", default="All", help='RNALocate source filter. Default: "All".')
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    parser.add_argument("--protocol-check-file", type=Path, help="Required protocol gate JSON for a formal run.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    queries = load_queries(rna_args=args.rna, input_path=args.input)
    if not queries:
        print("No RNA symbols were provided.", file=sys.stderr)
        return 2

    job_dir = args.job_dir or (DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{queries[0]}")
    temp_dir = job_dir / "temp"
    output_path = job_dir / OUTPUT_FILENAME
    raw_response_path = temp_dir / "raw_response.html"
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
            input_type=infer_input_type(query_count=len(queries), input_file=args.input),
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

    input_artifacts = copy_input_artifacts(input_path=args.input, queries=queries, temp_dir=temp_dir)
    rows: list[dict[str, str]] = []
    failures: dict[str, str] = {}
    raw_pages: list[str] = []
    urls: dict[str, str] = {}
    for query in queries:
        url = build_search_url(
            keyword=query,
            dataset=args.dataset,
            category=args.category,
            species=args.species,
            sources=args.sources,
        )
        urls[query] = url
        try:
            payload = fetch_search_html(url=url, timeout=args.timeout)
            rows.extend(parse_search_results(query_keyword=query, payload=payload))
            raw_pages.append(payload)
        except RNALocateError as exc:
            failures[query] = str(exc)

    query_success_count = len(queries) - len(failures)
    result_status = "success"
    if failures and query_success_count > 0:
        result_status = "partial_success"
    elif failures:
        result_status = "failed"

    write_table(output_path, RESULT_FIELDS, rows)
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_response_path.write_text("\n\n<!-- query break -->\n\n".join(raw_pages), encoding="utf-8")
    if failures:
        write_json(errors_path, failures)
    write_json(
        summary_path,
        {
            "_meta": {
                "page_key": PAGE_KEY,
                "task_key": TASK_KEY,
                "query_count": len(queries),
                "query_success_count": query_success_count,
                "query_failure_count": len(failures),
                "matched_row_count": len(rows),
                "result_status": result_status,
                "dataset": args.dataset,
                "category": args.category,
                "species": args.species,
                "sources": args.sources,
                "job_dir": str(job_dir),
                "output_path": str(output_path),
                "raw_response_path": str(raw_response_path),
                "protocol_check_file": str(args.protocol_check_file),
                "protocol_check": protocol_payload,
                "input_artifacts": input_artifacts,
                "query_urls": urls,
            },
            "results_by_query": {
                query: [row for row in rows if row["query_rna_symbol"] == query] for query in queries
            },
        },
    )
    print(f"Result TSV: {output_path}", file=sys.stderr)
    print(f"Raw HTML: {raw_response_path}", file=sys.stderr)
    print(f"Summary JSON: {summary_path}", file=sys.stderr)
    if failures:
        print(f"Errors JSON: {errors_path}", file=sys.stderr)
    if result_status == "failed":
        print("RNALocate failed for all queries.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
