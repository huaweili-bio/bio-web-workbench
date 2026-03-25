#!/usr/bin/env python3
"""mRSLPred task: predict localization and render PNG/PDF in one bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.github_com.raghavagps_mrslpred.common.figure import DEFAULT_TITLE, build_figure_summary_result, render_localization_figure
    from webpages.github_com.raghavagps_mrslpred.common.runtime import DEFAULT_CONDA_ENV_NAME, DEFAULT_HOMEPAGE, DEFAULT_WEB_SERVER, RESULT_FIELDS, THRESHOLD_DEFAULTS, build_prediction_summary_results, build_runtime_command, combine_prediction_rows, copy_input_artifacts, ensure_runtime_assets, parse_fasta_records, read_prediction_outputs, resolve_runtime_command, run_mrslpred, write_csv_rows, write_json
else:
    from ..common.figure import DEFAULT_TITLE, build_figure_summary_result, render_localization_figure
    from ..common.runtime import DEFAULT_CONDA_ENV_NAME, DEFAULT_HOMEPAGE, DEFAULT_WEB_SERVER, RESULT_FIELDS, THRESHOLD_DEFAULTS, build_prediction_summary_results, build_runtime_command, combine_prediction_rows, copy_input_artifacts, ensure_runtime_assets, parse_fasta_records, read_prediction_outputs, resolve_runtime_command, run_mrslpred, write_csv_rows, write_json

ROOT = Path(__file__).resolve().parents[5]
PAGE_KEY = "github_com.raghavagps_mrslpred"
TASK_KEY = "fasta_to_localization_bundle"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "RNALoc_mRSLPred"
DEFAULT_CACHE_DIR = ROOT / "outputs" / "cache" / "github_com__raghavagps_mrslpred"

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "mRNA",
    "bio_goal": "FASTA -> prediction result + PNG/PDF figure",
    "provider": "mRSLPred",
    "homepage": DEFAULT_HOMEPAGE,
    "interaction_mode": "local_runtime",
    "master_file_mode": "multi_file_bundle",
}
MASTER_FILE_NAME = "mrslpred_result.csv"
FIGURE_PNG_NAME = "mrslpred_localization_figure.png"
FIGURE_PDF_NAME = "mrslpred_localization_figure.pdf"

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mRSLPred and generate mrslpred_result.csv plus prefixed localization figure PNG/PDF.")
    parser.add_argument("--input", type=Path, help="Input FASTA file.")
    parser.add_argument("--input-dir", type=Path, help="NCBI bundle directory containing sequences.fasta.")
    parser.add_argument("--job-dir", type=Path, help="Preferred output directory.")
    parser.add_argument("--job-name", help="Optional label used to auto-build the job directory name.")
    parser.add_argument("--output-prefix", type=Path, help="Legacy output prefix for result/figure files.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help=f"Runtime cache directory (default: {DEFAULT_CACHE_DIR}).")
    parser.add_argument("--conda-env-name", default=DEFAULT_CONDA_ENV_NAME, help=f"Conda environment name (default: {DEFAULT_CONDA_ENV_NAME}).")
    parser.add_argument("--runtime-python", type=Path, help="Optional direct Python executable path for the mRSLPred runtime.")
    parser.add_argument("--title", default=DEFAULT_TITLE, help=f'Figure title (default: "{DEFAULT_TITLE}").')
    parser.add_argument("--th1", type=float, default=THRESHOLD_DEFAULTS["th1"], help="Ribosome threshold.")
    parser.add_argument("--th2", type=float, default=THRESHOLD_DEFAULTS["th2"], help="Cytosol threshold.")
    parser.add_argument("--th3", type=float, default=THRESHOLD_DEFAULTS["th3"], help="ER threshold.")
    parser.add_argument("--th4", type=float, default=THRESHOLD_DEFAULTS["th4"], help="Membrane threshold.")
    parser.add_argument("--th5", type=float, default=THRESHOLD_DEFAULTS["th5"], help="Nucleus threshold.")
    parser.add_argument("--th6", type=float, default=THRESHOLD_DEFAULTS["th6"], help="Exosome threshold.")
    return parser.parse_args(argv)

def resolve_input_fasta(args: argparse.Namespace) -> Path:
    if bool(args.input) == bool(args.input_dir):
        raise ValueError("Use exactly one of --input or --input-dir.")
    if args.input_dir:
        fasta_candidates = [
            args.input_dir / "recommended_transcripts.fasta",
            args.input_dir / "sequences.fasta",
        ]
        fasta_path = next((candidate for candidate in fasta_candidates if candidate.exists()), None)
        if fasta_path is None:
            raise ValueError(f"Could not find recommended_transcripts.fasta under input dir: {args.input_dir}")
        return fasta_path
    assert args.input is not None
    return args.input

def safe_filename(value: str) -> str:
    import re

    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    sanitized = sanitized.strip("._")
    return sanitized or "job"

def derive_job_name(args: argparse.Namespace, input_fasta: Path) -> str:
    if args.job_name:
        return safe_filename(args.job_name)
    if args.input_dir:
        return safe_filename(args.input_dir.name)
    return safe_filename(input_fasta.stem)

def resolve_job_dir(args: argparse.Namespace, input_fasta: Path) -> Path:
    if args.job_dir:
        return args.job_dir
    return DEFAULT_JOB_ROOT / f"{DEFAULT_JOB_TAG}_{derive_job_name(args, input_fasta)}"

def build_output_layout(*, args: argparse.Namespace, input_fasta: Path) -> dict[str, Path | str | None]:
    if args.job_dir and args.output_prefix:
        raise ValueError("Use either --job-dir or --output-prefix, not both.")
    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "master_csv_path": args.output_prefix.with_suffix(".mrslpred_result.csv"),
            "figure_png_path": args.output_prefix.with_suffix(".mrslpred_localization_figure.png"),
            "figure_pdf_path": args.output_prefix.with_suffix(".mrslpred_localization_figure.pdf"),
            "summary_path": args.output_prefix.with_suffix(".summary.json"),
            "errors_path": args.output_prefix.with_suffix(".errors.json"),
        }

    job_dir = resolve_job_dir(args, input_fasta)
    return {
        "mode": "job_dir",
        "job_dir": job_dir,
        "temp_dir": job_dir / "temp",
        "master_csv_path": job_dir / MASTER_FILE_NAME,
        "figure_png_path": job_dir / FIGURE_PNG_NAME,
        "figure_pdf_path": job_dir / FIGURE_PDF_NAME,
        "summary_path": job_dir / "temp" / "summary.json",
        "errors_path": job_dir / "temp" / "errors.json",
    }

def save_png_as_pdf(png_path: Path, pdf_path: Path) -> None:
    with Image.open(png_path) as image:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(pdf_path, "PDF", resolution=300.0)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        input_fasta = resolve_input_fasta(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not input_fasta.exists():
        print(f"Input FASTA does not exist: {input_fasta}", file=sys.stderr)
        return 2

    fasta_records = parse_fasta_records(input_fasta)

    try:
        layout = build_output_layout(args=args, input_fasta=input_fasta)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    input_artifacts = copy_input_artifacts(input_path=input_fasta, temp_dir=temp_dir)

    try:
        runtime_assets = ensure_runtime_assets(args.cache_dir)
    except Exception as exc:
        print(f"Failed to prepare mRSLPred runtime: {exc}", file=sys.stderr)
        return 1

    script_path = runtime_assets["script_path"]
    runtime_output_dir = (temp_dir or args.cache_dir) / "official_output"
    runtime_output_dir.mkdir(parents=True, exist_ok=True)
    runtime_command = build_runtime_command(args, script_path, input_fasta, runtime_output_dir)
    resolved_command, runtime_label = resolve_runtime_command(runtime_command)

    try:
        completed = run_mrslpred(command=runtime_command, working_directory=script_path.parent)
    except FileNotFoundError as exc:
        print(f"Failed to launch mRSLPred runtime: {exc}", file=sys.stderr)
        return 1

    runtime_stdout = completed.stdout.strip()
    runtime_stderr = completed.stderr.strip()
    if completed.returncode != 0:
        message = runtime_stderr or runtime_stdout or "Unknown mRSLPred runtime failure."
        print(message, file=sys.stderr)
        return 1

    try:
        label_rows, prob_rows = read_prediction_outputs(runtime_output_dir)
        result_rows, unmatched_ids = combine_prediction_rows(
            fasta_records=fasta_records,
            label_rows=label_rows,
            prob_rows=prob_rows,
        )
        render_info = render_localization_figure(
            rows=result_rows,
            output_path=layout["figure_png_path"],
            title=args.title,
        )
        save_png_as_pdf(layout["figure_png_path"], layout["figure_pdf_path"])
    except Exception as exc:
        write_json(layout["errors_path"], {"error": str(exc)})
        print(str(exc), file=sys.stderr)
        return 1

    write_csv_rows(layout["master_csv_path"], RESULT_FIELDS, result_rows)
    write_json(
        layout["summary_path"],
        {
            "_meta": {
                "task": TASK_METADATA,
                "homepage": DEFAULT_HOMEPAGE,
                "web_server": DEFAULT_WEB_SERVER,
                "input_fasta": str(input_fasta),
                "input_dir": str(args.input_dir) if args.input_dir else "",
                "query_sequence_count": len(fasta_records),
                "output_mode": layout["mode"],
                "master_file_path": str(layout["master_csv_path"]),
                "figure_png_path": str(layout["figure_png_path"]),
                "figure_pdf_path": str(layout["figure_pdf_path"]),
                "job_dir": str(layout["job_dir"]) if isinstance(layout["job_dir"], Path) else "",
                "temp_dir": str(temp_dir) if isinstance(temp_dir, Path) else "",
                "runtime_cache_dir": str(args.cache_dir),
                "runtime_root": str(runtime_assets["runtime_root"]),
                "runtime_output_dir": str(runtime_output_dir),
                "runtime_command": resolved_command,
                "runtime_label": runtime_label,
                "runtime_stdout": runtime_stdout,
                "runtime_stderr": runtime_stderr,
                "input_artifacts": input_artifacts,
                "thresholds": {
                    "ribosome": args.th1,
                    "cytosol": args.th2,
                    "er": args.th3,
                    "membrane": args.th4,
                    "nucleus": args.th5,
                    "exosome": args.th6,
                },
                "unmatched_sequence_ids": unmatched_ids,
                "render_info": render_info,
            },
            "prediction_results": build_prediction_summary_results(result_rows),
            "figure_result": build_figure_summary_result(result_rows),
        },
    )

    if unmatched_ids:
        write_json(
            layout["errors_path"],
            {sequence_id: "Prediction row was missing from official mRSLPred outputs." for sequence_id in unmatched_ids},
        )

    print(f"Result CSV: {layout['master_csv_path']}", file=sys.stderr)
    print(f"Figure PNG: {layout['figure_png_path']}", file=sys.stderr)
    print(f"Figure PDF: {layout['figure_pdf_path']}", file=sys.stderr)
    print(f"Summary JSON: {layout['summary_path']}", file=sys.stderr)
    if unmatched_ids:
        print(f"Errors JSON: {layout['errors_path']}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
