#!/usr/bin/env python3
"""NCBI task: resolve gene symbols and fetch recommended-transcript FASTA in one bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.ncbi_nlm_nih_gov.gene.common.fasta_fetch import DEFAULT_EFETCH_DOC, FASTA_DETAIL_FIELDS, NcbiFastaClient, NcbiFastaError, build_fasta_summary_entry, build_output_fasta_header, parse_fasta_response
    from webpages.ncbi_nlm_nih_gov.gene.common.gene_resolution import DEFAULT_DATASETS_DOC, DEFAULT_TAXON, GENE_DETAIL_FIELDS, NcbiGeneClient, NcbiGeneError, annotate_rows_with_query_count, build_gene_summary_entry, copy_gene_input_artifacts, load_genes, parse_product_report
    from webpages.ncbi_nlm_nih_gov.gene.common.io import safe_filename, wrap_fasta_sequence, write_csv_rows, write_json, write_text
else:
    from ..common.fasta_fetch import DEFAULT_EFETCH_DOC, FASTA_DETAIL_FIELDS, NcbiFastaClient, NcbiFastaError, build_fasta_summary_entry, build_output_fasta_header, parse_fasta_response
    from ..common.gene_resolution import DEFAULT_DATASETS_DOC, DEFAULT_TAXON, GENE_DETAIL_FIELDS, NcbiGeneClient, NcbiGeneError, annotate_rows_with_query_count, build_gene_summary_entry, copy_gene_input_artifacts, load_genes, parse_product_report
    from ..common.io import safe_filename, wrap_fasta_sequence, write_csv_rows, write_json, write_text

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_HOMEPAGE = "https://www.ncbi.nlm.nih.gov/"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
PAGE_KEY = "ncbi_nlm_nih_gov.gene"
TASK_KEY = "gene_set_to_fasta_bundle"
DEFAULT_JOB_TAG = "GeneSeq_NCBI_GeneBundle"
ALL_TRANSCRIPTS_FILENAME = "all_transcripts.csv"
RECOMMENDED_TRANSCRIPTS_FILENAME = "recommended_transcripts.csv"
FASTA_RESULT_FILENAME = "recommended_transcript_fasta_records.csv"
FASTA_FILENAME = "recommended_transcripts.fasta"
GENE_LIST_FILENAME = "query_genes.txt"

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "mRNA",
    "bio_goal": "gene symbol -> recommended-transcript sequence bundle",
    "provider": "NCBI",
    "homepage": DEFAULT_HOMEPAGE,
    "interaction_mode": "api",
    "master_file_mode": "multi_file_bundle",
}

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve gene symbols via NCBI, keep all/recommended transcripts, and fetch FASTA for the recommended transcript of each gene.",
    )
    parser.add_argument("--gene", action="append", default=[], help="Gene symbol. Repeat the flag or pass comma-separated values.")
    parser.add_argument("--input", type=Path, help="Input file. Supports text or CSV.")
    parser.add_argument("--job-dir", type=Path, help="Preferred output directory.")
    parser.add_argument("--job-name", help="Optional label used to auto-build the job directory name.")
    parser.add_argument("--output-prefix", type=Path, help="Legacy output prefix for combined outputs.")
    parser.add_argument("--taxon", default=DEFAULT_TAXON, help=f'Taxon name or ID (default: "{DEFAULT_TAXON}").')
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds.")
    return parser.parse_args(argv)

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
    return DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{safe_filename(args.taxon)}_{derive_job_name(args, genes)}"

def build_output_layout(*, args: argparse.Namespace, genes: list[str]) -> dict[str, Path | str | None]:
    if args.job_dir and args.output_prefix:
        raise NcbiGeneError("Use either --job-dir or --output-prefix, not both.")
    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "gene_list_path": args.output_prefix.with_suffix(".genes.txt"),
            "all_transcripts_csv_path": args.output_prefix.with_suffix(".all_transcripts.csv"),
            "recommended_csv_path": args.output_prefix.with_suffix(".recommended_transcripts.csv"),
            "fasta_result_csv_path": args.output_prefix.with_suffix(".fasta_result.csv"),
            "fasta_path": args.output_prefix.with_suffix(".fasta"),
            "summary_path": args.output_prefix.with_suffix(".summary.json"),
            "errors_path": args.output_prefix.with_suffix(".errors.json"),
        }

    job_dir = resolve_job_dir(args, genes)
    return {
        "mode": "job_dir",
        "job_dir": job_dir,
        "temp_dir": job_dir / "temp",
        "gene_list_path": job_dir / "temp" / GENE_LIST_FILENAME,
        "all_transcripts_csv_path": job_dir / "temp" / ALL_TRANSCRIPTS_FILENAME,
        "recommended_csv_path": job_dir / RECOMMENDED_TRANSCRIPTS_FILENAME,
        "fasta_result_csv_path": job_dir / "temp" / FASTA_RESULT_FILENAME,
        "fasta_path": job_dir / FASTA_FILENAME,
        "summary_path": job_dir / "temp" / "summary.json",
        "errors_path": job_dir / "temp" / "errors.json",
    }

def filter_recommended_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row.get("transcript_is_recommended") or 0) == 1]

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    genes = load_genes(gene_args=args.gene, input_path=args.input)
    if not genes:
        print("No gene inputs were provided.", file=sys.stderr)
        return 2

    try:
        layout = build_output_layout(args=args, genes=genes)
    except NcbiGeneError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    input_artifacts = copy_gene_input_artifacts(input_path=args.input, genes=genes, temp_dir=temp_dir)

    gene_client = NcbiGeneClient(timeout=args.timeout)
    fasta_client = NcbiFastaClient(timeout=args.timeout)
    all_rows: list[dict[str, Any]] = []
    gene_results: dict[str, Any] = {}
    gene_failures: dict[str, str] = {}
    unmatched_query_genes: list[str] = []
    gene_query_urls: dict[str, str] = {}

    for index, gene in enumerate(genes, start=1):
        print(f"[gene {index}/{len(genes)}] Querying {gene}", file=sys.stderr)
        try:
            query_url, payload = gene_client.fetch_product_report(gene, args.taxon)
            gene_query_urls[gene] = query_url
            product, rows = parse_product_report(payload, gene)
        except NcbiGeneError as exc:
            gene_failures[gene] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        gene_results[gene] = build_gene_summary_entry(product, rows)
        if not rows:
            unmatched_query_genes.append(gene)
            gene_failures[gene] = f"Gene symbol was not found in NCBI product_report for taxon '{args.taxon}'."
            print("  no transcript match", file=sys.stderr)
            continue

        annotate_rows_with_query_count(rows, gene_results[gene]["transcript_count"])
        all_rows.extend(rows)
        print(
            f"  {gene_results[gene]['transcript_count']} transcripts, recommended {gene_results[gene]['recommended_transcript_accession_version']}",
            file=sys.stderr,
        )

    all_rows.sort(key=lambda row: (str(row.get("query_gene_symbol") or ""), int(row.get("transcript_rank") or 0)))
    recommended_rows = filter_recommended_rows(all_rows)

    fasta_rows: list[dict[str, Any]] = []
    fasta_results: dict[str, Any] = {}
    fasta_failures: dict[str, str] = {}
    unmatched_recommended_transcripts: list[str] = []
    fasta_query_urls: dict[str, str] = {}
    fasta_chunks: list[str] = []

    for index, row in enumerate(recommended_rows, start=1):
        accession = str(row["transcript_accession_version"])
        print(f"[fasta {index}/{len(recommended_rows)}] Fetching {accession}", file=sys.stderr)
        try:
            query_url, payload = fasta_client.fetch_fasta_text(accession)
            fasta_query_urls[accession] = query_url
            accession_version, ncbi_header, sequence = parse_fasta_response(payload)
        except NcbiFastaError as exc:
            fasta_failures[accession] = str(exc)
            unmatched_recommended_transcripts.append(accession)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        fasta_row = {
            "query_transcript_accession": accession,
            "query_fasta_count": 1,
            "query_gene_symbol": row.get("query_gene_symbol", ""),
            "gene_symbol": row.get("gene_symbol", ""),
            "transcript_accession_version": accession_version,
            "transcript_accession": accession_version.split(".", 1)[0],
            "fasta_header": build_output_fasta_header(
                accession_version=accession_version,
                query_gene_symbol=str(row.get("query_gene_symbol", "")),
                gene_symbol=str(row.get("gene_symbol", "")),
            ),
            "ncbi_fasta_header": ncbi_header,
            "sequence_length": len(sequence),
        }
        fasta_rows.append(fasta_row)
        fasta_results[accession] = build_fasta_summary_entry(fasta_row)
        fasta_chunks.append(f">{fasta_row['fasta_header']}\n{wrap_fasta_sequence(sequence)}\n")
        print(f"  {len(sequence)} nt", file=sys.stderr)

    gene_list_path = layout["gene_list_path"]
    all_transcripts_csv_path = layout["all_transcripts_csv_path"]
    recommended_csv_path = layout["recommended_csv_path"]
    fasta_result_csv_path = layout["fasta_result_csv_path"]
    fasta_path = layout["fasta_path"]
    summary_path = layout["summary_path"]
    errors_path = layout["errors_path"]
    assert isinstance(gene_list_path, Path)
    assert isinstance(all_transcripts_csv_path, Path)
    assert isinstance(recommended_csv_path, Path)
    assert isinstance(fasta_result_csv_path, Path)
    assert isinstance(fasta_path, Path)
    assert isinstance(summary_path, Path)
    assert isinstance(errors_path, Path)

    gene_list_path.parent.mkdir(parents=True, exist_ok=True)
    gene_list_path.write_text("\n".join(genes) + "\n", encoding="utf-8")
    write_csv_rows(all_transcripts_csv_path, GENE_DETAIL_FIELDS, all_rows)
    write_csv_rows(recommended_csv_path, GENE_DETAIL_FIELDS, recommended_rows)
    write_csv_rows(fasta_result_csv_path, FASTA_DETAIL_FIELDS, fasta_rows)
    write_text(fasta_path, "".join(fasta_chunks))

    write_json(
        summary_path,
        {
            "_meta": {
                "task": TASK_METADATA,
                "homepage": DEFAULT_HOMEPAGE,
                "efetch_doc": DEFAULT_EFETCH_DOC,
                "query_genes": genes,
                "taxon": args.taxon,
                "output_mode": layout["mode"],
                "job_dir": str(layout["job_dir"]) if isinstance(layout["job_dir"], Path) else "",
                "temp_dir": str(temp_dir) if isinstance(temp_dir, Path) else "",
                "input_artifacts": input_artifacts,
                "gene_list_path": str(gene_list_path),
                "all_transcripts_csv_path": str(all_transcripts_csv_path),
                "recommended_transcripts_csv_path": str(recommended_csv_path),
                "fasta_result_csv_path": str(fasta_result_csv_path),
                "fasta_path": str(fasta_path),
                "all_transcript_row_count": len(all_rows),
                "recommended_transcript_row_count": len(recommended_rows),
                "fasta_row_count": len(fasta_rows),
                "query_urls": {
                    "gene_symbol_to_transcript": gene_query_urls,
                    "transcript_to_fasta": fasta_query_urls,
                },
                "unmatched_query_genes": unmatched_query_genes,
                "unmatched_recommended_transcripts": unmatched_recommended_transcripts,
            },
            "gene_symbol_to_transcript": gene_results,
            "transcript_to_fasta": fasta_results,
        },
    )

    combined_failures: dict[str, Any] = {}
    if gene_failures:
        combined_failures["gene_symbol_to_transcript"] = gene_failures
    if fasta_failures:
        combined_failures["transcript_to_fasta"] = fasta_failures
    if combined_failures:
        write_json(errors_path, combined_failures)

    print(f"Gene list: {gene_list_path}", file=sys.stderr)
    print(f"All transcripts CSV: {all_transcripts_csv_path}", file=sys.stderr)
    print(f"Recommended transcripts CSV: {recommended_csv_path}", file=sys.stderr)
    print(f"FASTA result CSV: {fasta_result_csv_path}", file=sys.stderr)
    print(f"FASTA: {fasta_path}", file=sys.stderr)
    print(f"Summary JSON: {summary_path}", file=sys.stderr)
    if combined_failures:
        print(f"Errors JSON: {errors_path}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
