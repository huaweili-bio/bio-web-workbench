from __future__ import annotations

import csv
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_HOMEPAGE = "https://github.com/raghavagps/mrslpred"
DEFAULT_WEB_SERVER = "https://webs.iiitd.edu.in/raghava/mrslpred/"
DEFAULT_CONDA_ENV_NAME = "mrslpred_py37"
USER_AGENT = "bio-script-mrslpred/1.0"
RUNTIME_REPO_API = "https://api.github.com/repos/raghavagps/mrslpred/contents"
RESULT_FIELDS = [
    "sequence_id", "transcript_accession_version", "transcript_accession", "query_gene_symbol", "gene_symbol",
    "ribosome_label", "cytosol_label", "er_label", "membrane_label", "nucleus_label", "exosome_label",
    "ribosome_score", "cytosol_score", "er_score", "membrane_score", "nucleus_score", "exosome_score",
    "predicted_locations", "predicted_location_count", "fasta_header",
]
LABEL_COLUMNS = [("Ribosome", "ribosome_label"), ("Cytosol", "cytosol_label"), ("ER", "er_label"), ("Membrane", "membrane_label"), ("Nucleus", "nucleus_label"), ("Exosome", "exosome_label")]
PROB_COLUMNS = [("Ribosome", "ribosome_score"), ("Cytosol", "cytosol_score"), ("ER", "er_score"), ("Membrane", "membrane_score"), ("Nucleus", "nucleus_score"), ("Exosome", "exosome_score")]
THRESHOLD_DEFAULTS = {"th1": 0.3079, "th2": 0.1468, "th3": 0.1156, "th4": 0.1958, "th5": 0.7028, "th6": 0.9961}
RUNTIME_ROOT_FILES = {
    "mrslpred_motif.py": "https://raw.githubusercontent.com/raghavagps/mrslpred/main/mrslpred_motif.py",
    "Nfeature_DNA.py": "https://raw.githubusercontent.com/raghavagps/mrslpred/main/Nfeature_DNA.py",
    "xgboost_final.pkl": "https://raw.githubusercontent.com/raghavagps/mrslpred/main/xgboost_final.pkl",
    "README.md": "https://raw.githubusercontent.com/raghavagps/mrslpred/main/README.md",
}


class MrslpredError(RuntimeError):
    """Raised when the local mRSLPred runtime fails."""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def parse_fasta_records(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    header = ""
    sequence_chunks: list[str] = []

    def flush() -> None:
        nonlocal header, sequence_chunks
        if not header:
            return
        tokens = header.split()
        sequence_id = tokens[0]
        meta: dict[str, str] = {}
        for token in tokens[1:]:
            if "=" in token:
                key, value = token.split("=", 1)
                meta[key.strip()] = value.strip()
        records.append(
            {
                "sequence_id": sequence_id,
                "transcript_accession_version": meta.get("transcript_accession_version", sequence_id),
                "transcript_accession": meta.get("transcript_accession", sequence_id.split(".", 1)[0]),
                "query_gene_symbol": meta.get("query_gene_symbol", ""),
                "gene_symbol": meta.get("gene_symbol", ""),
                "fasta_header": header,
                "sequence": "".join(sequence_chunks),
            }
        )
        header = ""
        sequence_chunks = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            flush()
            header = line[1:].strip()
        else:
            sequence_chunks.append(line)
    flush()
    if not records:
        raise MrslpredError(f"No FASTA records were found in: {path}")
    return records


def copy_input_artifacts(*, input_path: Path, temp_dir: Path | None) -> dict[str, str]:
    metadata = {"original_input_file": "", "copied_input_file": "", "normalized_input_file": ""}
    if temp_dir is None:
        return metadata
    temp_dir.mkdir(parents=True, exist_ok=True)
    copied_input = temp_dir / f"original_input{input_path.suffix or '.fa'}"
    shutil.copyfile(input_path, copied_input)
    normalized_input = temp_dir / "normalized_input.fasta"
    shutil.copyfile(input_path, normalized_input)
    metadata["original_input_file"] = str(input_path)
    metadata["copied_input_file"] = str(copied_input)
    metadata["normalized_input_file"] = str(normalized_input)
    return metadata


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.read())


def _read_repo_listing(relative_path: str) -> list[dict[str, Any]]:
    url = f"{RUNTIME_REPO_API}/{relative_path}".rstrip("/")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise MrslpredError(f"Unexpected GitHub API payload for runtime path: {relative_path}")
    return payload


def ensure_runtime_assets(cache_dir: Path) -> dict[str, Any]:
    runtime_root = cache_dir / "runtime"
    data_dir = runtime_root / "Data"
    motifs_dir = runtime_root / "motifs"
    runtime_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    motifs_dir.mkdir(parents=True, exist_ok=True)
    for filename, url in RUNTIME_ROOT_FILES.items():
        destination = runtime_root / filename
        if not destination.exists():
            _download(url, destination)
    for entry in _read_repo_listing("Data"):
        if entry.get("type") == "file":
            destination = data_dir / str(entry["name"])
            if not destination.exists():
                _download(str(entry["download_url"]), destination)
    for entry in _read_repo_listing("motifs"):
        if entry.get("type") == "file":
            destination = motifs_dir / str(entry["name"])
            if not destination.exists():
                _download(str(entry["download_url"]), destination)
    return {"runtime_root": runtime_root, "script_path": runtime_root / "mrslpred_motif.py", "data_dir": data_dir, "motifs_dir": motifs_dir}


def build_runtime_command(args: Any, script_path: Path, input_fasta: Path, output_dir: Path) -> list[str]:
    if getattr(args, "runtime_python", None):
        prefix = [str(args.runtime_python)]
        runtime_label = str(args.runtime_python)
    else:
        prefix = ["conda", "run", "-n", args.conda_env_name, "python"]
        runtime_label = f"conda:{args.conda_env_name}"
    command = prefix + [str(script_path), "--file", str(input_fasta), "--output", str(output_dir), "--th1", str(args.th1), "--th2", str(args.th2), "--th3", str(args.th3), "--th4", str(args.th4), "--th5", str(args.th5), "--th6", str(args.th6)]
    command.append(f"--runtime-label={runtime_label}")
    return command


def resolve_runtime_command(command: list[str]) -> tuple[list[str], str]:
    runtime_label = ""
    resolved: list[str] = []
    for item in command:
        if item.startswith("--runtime-label="):
            runtime_label = item.split("=", 1)[1]
        else:
            resolved.append(item)
    return resolved, runtime_label


def run_mrslpred(*, command: list[str], working_directory: Path) -> subprocess.CompletedProcess[str]:
    resolved_command, _ = resolve_runtime_command(command)
    return subprocess.run(resolved_command, cwd=str(working_directory), capture_output=True, text=True, check=False)


def read_prediction_outputs(output_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    label_path = output_dir / "final_prediction.csv"
    prob_path = output_dir / "final_prob_prediction.csv"
    if not label_path.exists():
        raise MrslpredError(f"Official mRSLPred output is missing: {label_path}")
    if not prob_path.exists():
        raise MrslpredError(f"Official mRSLPred probability output is missing: {prob_path}")
    with label_path.open("r", encoding="utf-8", newline="") as handle:
        label_rows = list(csv.DictReader(handle))
    with prob_path.open("r", encoding="utf-8", newline="") as handle:
        prob_rows = list(csv.DictReader(handle))
    return label_rows, prob_rows


def combine_prediction_rows(*, fasta_records: list[dict[str, str]], label_rows: list[dict[str, str]], prob_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    labels_by_id = {row["Seq ID"]: row for row in label_rows}
    probs_by_id = {row["Seq ID"]: row for row in prob_rows}
    unmatched_ids: list[str] = []
    combined_rows: list[dict[str, Any]] = []
    for record in fasta_records:
        sequence_id = record["sequence_id"]
        label_row = labels_by_id.get(sequence_id)
        prob_row = probs_by_id.get(sequence_id)
        if label_row is None or prob_row is None:
            unmatched_ids.append(sequence_id)
            continue
        row: dict[str, Any] = {
            "sequence_id": sequence_id,
            "transcript_accession_version": record["transcript_accession_version"],
            "transcript_accession": record["transcript_accession"],
            "query_gene_symbol": record["query_gene_symbol"],
            "gene_symbol": record["gene_symbol"],
            "fasta_header": record["fasta_header"],
        }
        predicted_locations: list[str] = []
        for source_column, target_column in LABEL_COLUMNS:
            value = str(label_row.get(source_column, "")).strip()
            row[target_column] = value
            if value == "Yes":
                predicted_locations.append(source_column)
        for source_column, target_column in PROB_COLUMNS:
            row[target_column] = str(prob_row.get(source_column, "")).strip()
        row["predicted_locations"] = ";".join(predicted_locations)
        row["predicted_location_count"] = len(predicted_locations)
        combined_rows.append(row)
    combined_rows.sort(key=lambda item: item["sequence_id"])
    return combined_rows, unmatched_ids


def build_prediction_summary_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        row["sequence_id"]: {
            "query_gene_symbol": row["query_gene_symbol"],
            "gene_symbol": row["gene_symbol"],
            "transcript_accession_version": row["transcript_accession_version"],
            "predicted_locations": row["predicted_locations"].split(";") if row["predicted_locations"] else [],
            "predicted_location_count": row["predicted_location_count"],
        }
        for row in rows
    }
