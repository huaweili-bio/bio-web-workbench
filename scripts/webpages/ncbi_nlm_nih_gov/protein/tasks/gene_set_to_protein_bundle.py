#!/usr/bin/env python3
"""NCBI task: resolve gene symbols and fetch recommended-protein FASTA in one bundle."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.ncbi_nlm_nih_gov.protein.common.fasta_fetch import DEFAULT_EFETCH_DOC, FASTA_DETAIL_FIELDS, NcbiProteinFastaClient, NcbiProteinFastaError, build_fasta_summary_entry, build_output_fasta_header, parse_fasta_response
    from webpages.ncbi_nlm_nih_gov.protein.common.gene_resolution import DEFAULT_DATASETS_DOC, DEFAULT_TAXON, PRODUCT_DETAIL_FIELDS, NcbiProteinClient, NcbiProteinError, annotate_rows_with_query_count, build_gene_summary_entry, copy_gene_input_artifacts, load_genes, parse_product_report
    from webpages.ncbi_nlm_nih_gov.protein.common.io import safe_filename, wrap_fasta_sequence, write_csv_rows, write_json
else:
    from ..common.fasta_fetch import DEFAULT_EFETCH_DOC, FASTA_DETAIL_FIELDS, NcbiProteinFastaClient, NcbiProteinFastaError, build_fasta_summary_entry, build_output_fasta_header, parse_fasta_response
    from ..common.gene_resolution import DEFAULT_DATASETS_DOC, DEFAULT_TAXON, PRODUCT_DETAIL_FIELDS, NcbiProteinClient, NcbiProteinError, annotate_rows_with_query_count, build_gene_summary_entry, copy_gene_input_artifacts, load_genes, parse_product_report
    from ..common.io import safe_filename, wrap_fasta_sequence, write_csv_rows, write_json

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_HOMEPAGE = "https://www.ncbi.nlm.nih.gov/"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
PAGE_KEY = "ncbi_nlm_nih_gov.protein"
TASK_KEY = "gene_set_to_protein_bundle"
DEFAULT_JOB_TAG = "ProteinSeq_NCBI_ProteinBundle"
ALL_PRODUCTS_FILENAME = "matched_gene_summary.csv"
ALL_PROTEINS_FILENAME = "all_proteins.csv"
RECOMMENDED_PROTEINS_FILENAME = "recommended_proteins.csv"
FASTA_RESULT_FILENAME = "recommended_protein_fasta_records.csv"
FASTA_FILENAME = "recommended_proteins.fasta"
GENE_LIST_FILENAME = "query_genes.txt"

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "protein",
    "bio_goal": "gene symbol -> recommended-protein sequence bundle",
    "provider": "NCBI",
    "homepage": DEFAULT_HOMEPAGE,
    "interaction_mode": "api",
    "master_file_mode": "multi_file_bundle",
}

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve gene symbols via NCBI, keep all/recommended proteins, and fetch FASTA for the recommended protein of each gene.",
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
        raise NcbiProteinError("Use either --job-dir or --output-prefix, not both.")
    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "gene_list_path": args.output_prefix.with_suffix(".genes.txt"),
            "all_products_csv_path": args.output_prefix.with_suffix(".all_genes_or_products.csv"),
            "all_proteins_csv_path": args.output_prefix.with_suffix(".all_proteins.csv"),
            "recommended_csv_path": args.output_prefix.with_suffix(".recommended_proteins.csv"),
            "fasta_result_csv_path": args.output_prefix.with_suffix(".fasta_result.csv"),
            "fasta_path": args.output_prefix.with_suffix(".protein.fasta"),
            "summary_path": args.output_prefix.with_suffix(".summary.json"),
            "errors_path": args.output_prefix.with_suffix(".errors.json"),
        }

    job_dir = resolve_job_dir(args, genes)
    return {
        "mode": "job_dir",
        "job_dir": job_dir,
        "temp_dir": job_dir / "temp",
        "gene_list_path": job_dir / "temp" / GENE_LIST_FILENAME,
        "all_products_csv_path": job_dir / "temp" / ALL_PRODUCTS_FILENAME,
        "all_proteins_csv_path": job_dir / "temp" / ALL_PROTEINS_FILENAME,
        "recommended_csv_path": job_dir / RECOMMENDED_PROTEINS_FILENAME,
        "fasta_result_csv_path": job_dir / "temp" / FASTA_RESULT_FILENAME,
        "fasta_path": job_dir / FASTA_FILENAME,
        "summary_path": job_dir / "temp" / "summary.json",
        "errors_path": job_dir / "temp" / "errors.json",
    }

def filter_recommended_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row.get("protein_is_recommended") or 0) == 1]

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    genes = load_genes(gene_args=args.gene, input_path=args.input)
    if not genes:
        print("No gene inputs were provided.", file=sys.stderr)
        return 2

    try:
        layout = build_output_layout(args=args, genes=genes)
    except NcbiProteinError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    input_artifacts = copy_gene_input_artifacts(input_path=args.input, genes=genes, temp_dir=temp_dir)

    gene_client = NcbiProteinClient(timeout=args.timeout)
    fasta_client = NcbiProteinFastaClient(timeout=args.timeout)
    product_rows: list[dict[str, Any]] = []
    gene_summaries: list[dict[str, Any]] = []
    gene_summary_map: dict[str, Any] = {}
    gene_failures: dict[str, str] = {}

    for index, gene in enumerate(genes, start=1):
        print(f"[gene {index}/{len(genes)}] Querying {gene}", file=sys.stderr)
        try:
            query_url, payload = gene_client.fetch_product_report(gene, args.taxon)
            product, rows = parse_product_report(payload, gene)
        except NcbiProteinError as exc:
            gene_failures[gene] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        if not rows:
            gene_failures[gene] = f"Gene symbol was not found in NCBI product_report with protein products for taxon '{args.taxon}'."
            print("  no protein product match", file=sys.stderr)
            continue

        summary_entry = build_gene_summary_entry(product, rows)
        summary_entry["query_gene_symbol"] = gene
        summary_entry["query_url"] = query_url
        gene_summaries.append(summary_entry)
        gene_summary_map[gene] = summary_entry
        annotate_rows_with_query_count(rows, summary_entry["protein_count"])
        product_rows.extend(rows)
        print(
            f"  {summary_entry['protein_count']} proteins, recommended {summary_entry['recommended_protein_accession_version']}",
            file=sys.stderr,
        )

    product_rows.sort(key=lambda row: (str(row.get("query_gene_symbol") or ""), int(row.get("protein_rank") or 0)))
    recommended_rows = filter_recommended_rows(product_rows)

    fasta_rows: list[dict[str, Any]] = []
    fasta_results: dict[str, Any] = {}
    fasta_failures: dict[str, str] = {}
    fasta_chunks: list[str] = []
    for index, row in enumerate(recommended_rows, start=1):
        accession = str(row["protein_accession_version"])
        print(f"[fasta {index}/{len(recommended_rows)}] Fetching {accession}", file=sys.stderr)
        try:
            _, payload = fasta_client.fetch_fasta_text(accession)
            accession_version, ncbi_header, sequence = parse_fasta_response(payload)
        except NcbiProteinFastaError as exc:
            fasta_failures[accession] = str(exc)
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        fasta_row = {
            "query_gene_symbol": row.get("query_gene_symbol", ""),
            "gene_symbol": row.get("gene_symbol", ""),
            "transcript_accession_version": row.get("transcript_accession_version", ""),
            "protein_accession_version": accession_version,
            "protein_accession": accession_version.split(".", 1)[0],
            "protein_name": row.get("protein_name", ""),
            "fasta_header": build_output_fasta_header(
                accession_version=accession_version,
                query_gene_symbol=str(row.get("query_gene_symbol", "")),
                gene_symbol=str(row.get("gene_symbol", "")),
                transcript_accession_version=str(row.get("transcript_accession_version", "")),
            ),
            "ncbi_fasta_header": ncbi_header,
            "sequence_length": len(sequence),
        }
        fasta_rows.append(fasta_row)
        fasta_results[accession] = build_fasta_summary_entry(fasta_row)
        fasta_chunks.append(f">{fasta_row['fasta_header']}\n{wrap_fasta_sequence(sequence)}\n")
        print(f"  {len(sequence)} aa", file=sys.stderr)

    gene_list_path = layout["gene_list_path"]
    all_products_csv_path = layout["all_products_csv_path"]
    all_proteins_csv_path = layout["all_proteins_csv_path"]
    recommended_csv_path = layout["recommended_csv_path"]
    fasta_result_csv_path = layout["fasta_result_csv_path"]
    fasta_path = layout["fasta_path"]
    summary_path = layout["summary_path"]
    errors_path = layout["errors_path"]
    assert isinstance(gene_list_path, Path)
    assert isinstance(all_products_csv_path, Path)
    assert isinstance(all_proteins_csv_path, Path)
    assert isinstance(recommended_csv_path, Path)
    assert isinstance(fasta_result_csv_path, Path)
    assert isinstance(fasta_path, Path)
    assert isinstance(summary_path, Path)
    assert isinstance(errors_path, Path)

    gene_list_path.parent.mkdir(parents=True, exist_ok=True)
    gene_list_path.write_text("\n".join(genes) + "\n", encoding="utf-8")
    summary_fields = list(gene_summaries[0].keys()) if gene_summaries else ["query_gene_symbol"]
    write_csv_rows(all_products_csv_path, summary_fields, gene_summaries)
    write_csv_rows(all_proteins_csv_path, PRODUCT_DETAIL_FIELDS, product_rows)
    write_csv_rows(recommended_csv_path, PRODUCT_DETAIL_FIELDS, recommended_rows)
    write_csv_rows(fasta_result_csv_path, FASTA_DETAIL_FIELDS, fasta_rows)
    fasta_path.write_text("".join(fasta_chunks), encoding="utf-8")

    errors_payload: dict[str, Any] = {}
    if gene_failures:
        errors_payload["gene_failures"] = gene_failures
    if fasta_failures:
        errors_payload["fasta_failures"] = fasta_failures
    if errors_payload:
        write_json(errors_path, errors_payload)

    write_json(
        summary_path,
        {
            "_meta": {
                "task": TASK_METADATA,
                "homepage": DEFAULT_HOMEPAGE,
                "datasets_doc": DEFAULT_DATASETS_DOC,
                "efetch_doc": DEFAULT_EFETCH_DOC,
                "taxon": args.taxon,
                "query_gene_count": len(genes),
                "matched_gene_count": len(gene_summaries),
                "recommended_protein_count": len(recommended_rows),
                "fasta_sequence_count": len(fasta_rows),
                "output_mode": layout["mode"],
                "job_dir": str(layout["job_dir"]) if isinstance(layout["job_dir"], Path) else "",
                "temp_dir": str(temp_dir) if isinstance(temp_dir, Path) else "",
                "input_artifacts": input_artifacts,
                "all_products_csv_path": str(all_products_csv_path),
                "all_proteins_csv_path": str(all_proteins_csv_path),
                "recommended_proteins_csv_path": str(recommended_csv_path),
                "result_csv_path": str(fasta_result_csv_path),
                "protein_fasta_path": str(fasta_path),
            },
            "gene_results": gene_summary_map,
            "fasta_results": fasta_results,
        },
    )

    print(f"All products CSV: {all_products_csv_path}", file=sys.stderr)
    print(f"All proteins CSV: {all_proteins_csv_path}", file=sys.stderr)
    print(f"Recommended proteins CSV: {recommended_csv_path}", file=sys.stderr)
    print(f"Result CSV: {fasta_result_csv_path}", file=sys.stderr)
    print(f"Protein FASTA: {fasta_path}", file=sys.stderr)
    print(f"Summary JSON: {summary_path}", file=sys.stderr)
    if errors_payload:
        print(f"Errors JSON: {errors_path}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
