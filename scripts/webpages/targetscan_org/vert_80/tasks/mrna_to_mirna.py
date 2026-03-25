#!/usr/bin/env python3
"""TargetScanHuman 8.0 task: query gene symbols to mature miRNA predicted target details."""

from __future__ import annotations

import argparse
import csv
import http.client
import shutil
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from typing import Any
from urllib import error, request
from zipfile import BadZipFile, ZipFile

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from webpages.targetscan_org.vert_80.common.io import safe_filename, write_csv_rows, write_json
else:
    from ..common.io import safe_filename, write_csv_rows, write_json

PAGE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[5]
DEFAULT_HOMEPAGE = "https://www.targetscan.org/vert_80/"
DEFAULT_JOB_ROOT = ROOT / "outputs" / "tasks"
DEFAULT_JOB_TAG = "mRNA_miRNA_TargetScan"
DEFAULT_CACHE_DIR = ROOT / "outputs" / "cache" / "targetscan_org__vert_80"
DEFAULT_LOCAL_DATA_DIR = PAGE_DIR / "local_data"
USER_AGENT = "bio-script-targetscan/1.0"
PAGE_KEY = "targetscan_org.vert_80"
TASK_KEY = "mrna_to_mirna"
HUMAN_SPECIES_ID = "9606"
INPUT_COLUMN_CANDIDATES = ["gene_symbol", "gene", "symbol", "mrna", "biomarker"]
MASTER_FILE_NAME = "targetscanhuman_result.csv"
LOCAL_ONLY_ARCHIVE_KEYS = {"conserved_scores", "nonconserved_scores"}

ARCHIVE_SPECS: dict[str, dict[str, str]] = {
    "mir_family_info": {
        "url": "https://www.targetscan.org/vert_80/vert_80_data_download/miR_Family_Info.txt.zip",
        "member": "miR_Family_Info.txt",
    },
    "conserved_family_info": {
        "url": "https://www.targetscan.org/vert_80/vert_80_data_download/Conserved_Family_Info.txt.zip",
        "member": "Conserved_Family_Info.txt",
    },
    "nonconserved_family_info": {
        "url": "https://www.targetscan.org/vert_80/vert_80_data_download/Nonconserved_Family_Info.txt.zip",
        "member": "Nonconserved_Family_Info.txt",
    },
    "conserved_scores": {
        "url": "https://www.targetscan.org/vert_80/vert_80_data_download/Conserved_Site_Context_Scores.txt.zip",
        "member": "Conserved_Site_Context_Scores.txt",
    },
    "nonconserved_scores": {
        "url": "https://www.targetscan.org/vert_80/vert_80_data_download/Nonconserved_Site_Context_Scores.txt.zip",
        "member": "Nonconserved_Site_Context_Scores.txt",
    },
}

TASK_METADATA = {
    "task_key": TASK_KEY,
    "bio_category": "mRNA",
    "bio_goal": "mRNA biomarker -> mature miRNA predicted target details",
    "provider": "TargetScanHuman 8.0",
    "homepage": DEFAULT_HOMEPAGE,
    "source_zip_urls": [spec["url"] for spec in ARCHIVE_SPECS.values()],
    "interaction_mode": "download_table",
    "master_file_mode": "direct_generated_master_file",
}

DETAIL_FIELDS = [
    "query_gene_symbol",
    "query_transcript_count",
    "query_mirna_count",
    "query_site_count",
    "gene_id",
    "gene_symbol",
    "transcript_id",
    "gene_tax_id",
    "mirna",
    "mirna_family",
    "site_conservation",
    "site_type_code",
    "seed_match",
    "utr_start",
    "utr_end",
    "utr_position",
    "context_pp_score",
    "context_pp_score_percentile",
    "weighted_context_pp_score",
    "weighted_context_pp_score_percentile",
    "pct",
    "predicted_relative_kd",
]

SITE_TYPE_LABELS = {
    "1": "7mer-1A",
    "2": "7mer-m8",
    "3": "8mer",
    "-2": "7mer-m8",
    "-3": "8mer",
}

class TargetScanError(RuntimeError):
    """Raised when the TargetScanHuman dataset cannot be accessed or parsed safely."""

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch query TargetScanHuman 8.0 and export mature miRNA predicted target details for human gene symbols.",
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
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"Directory used to cache official TargetScanHuman ZIP downloads (default: {DEFAULT_CACHE_DIR}).",
    )
    parser.add_argument(
        "--local-mode",
        action="store_true",
        help="Use local score ZIP files from --local-data-dir instead of downloading the two large score archives.",
    )
    parser.add_argument(
        "--local-data-dir",
        type=Path,
        default=DEFAULT_LOCAL_DATA_DIR,
        help=f"Directory used by --local-mode for predownloaded large score archives (default: {DEFAULT_LOCAL_DATA_DIR}).",
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
        raise TargetScanError("Use either --job-dir or --output-prefix, not both.")

    if args.output_prefix:
        return {
            "mode": "legacy_prefix",
            "job_dir": None,
            "temp_dir": None,
            "master_csv_path": args.output_prefix.with_suffix(".targetscanhuman_result.csv"),
            "summary_path": args.output_prefix.with_suffix(".summary.json"),
            "errors_path": args.output_prefix.with_suffix(".errors.json"),
        }

    job_dir = resolve_job_dir(args, genes)
    temp_dir = job_dir / "temp"
    return {
        "mode": "job_dir",
        "job_dir": job_dir,
        "temp_dir": temp_dir,
        "master_csv_path": job_dir / MASTER_FILE_NAME,
        "summary_path": temp_dir / "summary.json",
        "errors_path": temp_dir / "errors.json",
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

def download_with_retries(url: str, destination: Path, *, timeout: float = 120.0, max_retries: int = 4) -> None:
    opener = request.build_opener()
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        ("Accept", "application/zip,*/*"),
        ("Connection", "close"),
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(f"{destination.name}.part")
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            with opener.open(url, timeout=timeout) as response, temp_path.open("wb") as handle:
                shutil.copyfileobj(response, handle, length=1024 * 1024)
            temp_path.replace(destination)
            return
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = exc
            if temp_path.exists():
                temp_path.unlink()
            if exc.code >= 500 and attempt < max_retries:
                time.sleep(min(2**attempt, 15))
                continue
            raise TargetScanError(f"HTTP {exc.code} while downloading {url}: {body[:400]}") from exc
        except (error.URLError, TimeoutError, http.client.IncompleteRead, OSError) as exc:
            last_error = exc
            if temp_path.exists():
                temp_path.unlink()
            if attempt < max_retries:
                time.sleep(min(2**attempt, 15))
                continue
            raise TargetScanError(f"Failed to download {url}: {exc}") from exc

    raise TargetScanError(f"Failed to download {url}: {last_error}")

def ensure_archive(cache_dir: Path, spec: dict[str, str]) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = spec["url"].rsplit("/", 1)[-1]
    archive_path = cache_dir / filename
    if archive_path.exists():
        return archive_path

    print(f"Initializing TargetScan cache: downloading {spec['url']}", file=sys.stderr)
    download_with_retries(spec["url"], archive_path)
    return archive_path

def ensure_required_archives(
    cache_dir: Path,
    *,
    local_mode: bool = False,
    local_data_dir: Path = DEFAULT_LOCAL_DATA_DIR,
) -> dict[str, Path]:
    archive_paths: dict[str, Path] = {}
    for name, spec in ARCHIVE_SPECS.items():
        filename = spec["url"].rsplit("/", 1)[-1]
        local_path = local_data_dir / filename
        if local_mode and name in LOCAL_ONLY_ARCHIVE_KEYS:
            if not local_path.exists():
                raise TargetScanError(
                    f"Local mode requires {filename} in {local_data_dir}, but the file was not found."
                )
            archive_paths[name] = local_path
            continue
        archive_paths[name] = ensure_archive(cache_dir, spec)
    return archive_paths

def fetch_remote_content_length(url: str, *, timeout: float = 60.0) -> int:
    attempts = [
        request.Request(url, method="HEAD"),
        request.Request(url, headers={"Range": "bytes=0-0"}, method="GET"),
    ]
    last_error: Exception | None = None

    for req in attempts:
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Connection", "close")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length:
                    return int(content_length)

                content_range = response.headers.get("Content-Range")
                if content_range and "/" in content_range:
                    return int(content_range.rsplit("/", 1)[-1])
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise TargetScanError(f"Failed to query remote file size for {url}: {last_error}")

def compare_local_mode_archives_to_remote(
    archive_paths: dict[str, Path],
) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}

    for name in sorted(LOCAL_ONLY_ARCHIVE_KEYS):
        spec = ARCHIVE_SPECS[name]
        local_path = archive_paths[name]
        local_size = local_path.stat().st_size
        result: dict[str, Any] = {
            "path": str(local_path),
            "local_size": local_size,
            "remote_size": None,
            "status": "remote_size_unknown",
            "message": "",
        }

        try:
            remote_size = fetch_remote_content_length(spec["url"])
        except TargetScanError as exc:
            result["message"] = str(exc)
            checks[name] = result
            print(f"Warning: {exc}", file=sys.stderr)
            continue

        result["remote_size"] = remote_size
        if remote_size == local_size:
            result["status"] = "match"
            checks[name] = result
            continue

        if remote_size > local_size:
            result["status"] = "remote_larger"
            result["message"] = (
                f"Remote file is larger than the local copy for {spec['url']} "
                f"(remote={remote_size}, local={local_size}). TargetScan may have updated. "
                "Refresh the local data file before rerunning local-mode."
            )
            checks[name] = result
            raise TargetScanError(result["message"])

        result["status"] = "remote_smaller"
        result["message"] = (
            f"Remote size for {spec['url']} is smaller than the local copy "
            f"(remote={remote_size}, local={local_size}). Continuing with the local file."
        )
        checks[name] = result
        print(f"Warning: {result['message']}", file=sys.stderr)

    return checks

def load_mirna_family_lookup(mir_family_zip_path: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    member_name = ARCHIVE_SPECS["mir_family_info"]["member"]
    try:
        with ZipFile(mir_family_zip_path) as archive:
            with archive.open(member_name) as raw_handle:
                text_handle = TextIOWrapper(raw_handle, encoding="utf-8", newline="")
                try:
                    reader = csv.DictReader(text_handle, delimiter="\t")
                    for row in reader:
                        if row.get("Species ID") != HUMAN_SPECIES_ID:
                            continue
                        mirna = str(row.get("MiRBase ID") or "").strip()
                        family = str(row.get("miR family") or "").strip()
                        if mirna and family:
                            lookup[mirna] = family
                finally:
                    text_handle.detach()
    except FileNotFoundError as exc:
        raise TargetScanError(f"Cached ZIP does not exist: {mir_family_zip_path}") from exc
    except BadZipFile as exc:
        raise TargetScanError(f"Cached ZIP is invalid: {mir_family_zip_path}") from exc
    return lookup

def collect_family_info_for_queries(
    zip_path: Path,
    *,
    member_name: str,
    query_genes: list[str],
) -> dict[str, dict[tuple[str, str, str, str, str, str, str], dict[str, str]]]:
    query_lookup = {query_gene.casefold(): query_gene for query_gene in query_genes}
    rows_by_query: dict[str, dict[tuple[str, str, str, str, str, str, str], dict[str, str]]] = {
        query_gene: {} for query_gene in query_genes
    }

    try:
        with ZipFile(zip_path) as archive:
            if member_name not in archive.namelist():
                raise TargetScanError(f"Cached ZIP {zip_path} does not contain {member_name}.")
            with archive.open(member_name) as raw_handle:
                text_handle = TextIOWrapper(raw_handle, encoding="utf-8", newline="")
                try:
                    reader = csv.DictReader(text_handle, delimiter="\t")
                    for row in reader:
                        if row.get("Species ID") != HUMAN_SPECIES_ID:
                            continue

                        gene_symbol = str(row.get("Gene Symbol") or "").strip()
                        query_gene = query_lookup.get(gene_symbol.casefold())
                        if query_gene is None:
                            continue

                        key = (
                            str(row.get("Gene ID") or "").strip(),
                            gene_symbol,
                            str(row.get("Transcript ID") or "").strip(),
                            HUMAN_SPECIES_ID,
                            str(row.get("UTR start") or "").strip(),
                            str(row.get("UTR end") or "").strip(),
                            str(row.get("miR Family") or "").strip(),
                        )
                        rows_by_query[query_gene][key] = {
                            "seed_match": str(row.get("Seed match") or "").strip(),
                            "pct": str(row.get("PCT") or "").strip(),
                        }
                finally:
                    text_handle.detach()
    except FileNotFoundError as exc:
        raise TargetScanError(f"Cached ZIP does not exist: {zip_path}") from exc
    except BadZipFile as exc:
        raise TargetScanError(f"Cached ZIP is invalid: {zip_path}") from exc
    return rows_by_query

def normalize_pct(value: str, site_conservation: str) -> str:
    stripped = value.strip()
    if stripped:
        return stripped
    if site_conservation == "nonconserved":
        return "N/A"
    return ""

def lookup_seed_match(raw_site_type: str, family_info: dict[str, str]) -> str:
    if family_info.get("seed_match"):
        return family_info["seed_match"]
    return SITE_TYPE_LABELS.get(raw_site_type.strip(), raw_site_type.strip())

def flatten_score_row(
    *,
    query_gene_symbol: str,
    row: dict[str, str],
    site_conservation: str,
    mirna_family_lookup: dict[str, str],
    family_info_lookup: dict[tuple[str, str, str, str, str, str, str], dict[str, str]],
) -> dict[str, Any]:
    gene_id = str(row.get("Gene ID") or "").strip()
    gene_symbol = str(row.get("Gene Symbol") or "").strip()
    transcript_id = str(row.get("Transcript ID") or "").strip()
    gene_tax_id = str(row.get("Gene Tax ID") or "").strip()
    mirna = str(row.get("miRNA") or "").strip()
    utr_start = str(row.get("UTR_start") or "").strip()
    utr_end = str(row.get("UTR end") or "").strip()
    site_type_code = str(row.get("Site Type") or "").strip()
    mirna_family = mirna_family_lookup.get(mirna, "")
    family_info = family_info_lookup.get(
        (gene_id, gene_symbol, transcript_id, gene_tax_id, utr_start, utr_end, mirna_family),
        {},
    )
    return {
        "query_gene_symbol": query_gene_symbol,
        "query_transcript_count": 0,
        "query_mirna_count": 0,
        "query_site_count": 0,
        "gene_id": gene_id,
        "gene_symbol": gene_symbol,
        "transcript_id": transcript_id,
        "gene_tax_id": gene_tax_id,
        "mirna": mirna,
        "mirna_family": mirna_family,
        "site_conservation": site_conservation,
        "site_type_code": site_type_code,
        "seed_match": lookup_seed_match(site_type_code, family_info),
        "utr_start": utr_start,
        "utr_end": utr_end,
        "utr_position": f"{utr_start}-{utr_end}" if utr_start and utr_end else "",
        "context_pp_score": str(row.get("context++ score") or "").strip(),
        "context_pp_score_percentile": str(row.get("context++ score percentile") or "").strip(),
        "weighted_context_pp_score": str(row.get("weighted context++ score") or "").strip(),
        "weighted_context_pp_score_percentile": str(row.get("weighted context++ score percentile") or "").strip(),
        "pct": normalize_pct(family_info.get("pct", ""), site_conservation),
        "predicted_relative_kd": str(row.get("Predicted relative KD") or "").strip(),
    }

def collect_score_rows_for_queries(
    zip_path: Path,
    *,
    member_name: str,
    query_genes: list[str],
    site_conservation: str,
    mirna_family_lookup: dict[str, str],
    family_info_by_query: dict[str, dict[tuple[str, str, str, str, str, str, str], dict[str, str]]],
) -> dict[str, list[dict[str, Any]]]:
    query_lookup = {query_gene.casefold(): query_gene for query_gene in query_genes}
    rows_by_query = {query_gene: [] for query_gene in query_genes}

    try:
        with ZipFile(zip_path) as archive:
            if member_name not in archive.namelist():
                raise TargetScanError(f"Cached ZIP {zip_path} does not contain {member_name}.")
            with archive.open(member_name) as raw_handle:
                text_handle = TextIOWrapper(raw_handle, encoding="utf-8", newline="")
                try:
                    reader = csv.DictReader(text_handle, delimiter="\t")
                    for row in reader:
                        if row.get("Gene Tax ID") != HUMAN_SPECIES_ID:
                            continue

                        gene_symbol = str(row.get("Gene Symbol") or "").strip()
                        query_gene = query_lookup.get(gene_symbol.casefold())
                        if query_gene is None:
                            continue

                        rows_by_query[query_gene].append(
                            flatten_score_row(
                                query_gene_symbol=query_gene,
                                row=row,
                                site_conservation=site_conservation,
                                mirna_family_lookup=mirna_family_lookup,
                                family_info_lookup=family_info_by_query[query_gene],
                            )
                        )
                finally:
                    text_handle.detach()
    except FileNotFoundError as exc:
        raise TargetScanError(f"Cached ZIP does not exist: {zip_path}") from exc
    except BadZipFile as exc:
        raise TargetScanError(f"Cached ZIP is invalid: {zip_path}") from exc

    return rows_by_query

def merge_rows_by_query(
    *,
    query_genes: list[str],
    conserved_rows: dict[str, list[dict[str, Any]]],
    nonconserved_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    merged = {query_gene: [] for query_gene in query_genes}
    for query_gene in query_genes:
        merged_rows = [*conserved_rows.get(query_gene, []), *nonconserved_rows.get(query_gene, [])]
        merged_rows.sort(
            key=lambda row: (
                str(row.get("query_gene_symbol") or ""),
                str(row.get("gene_symbol") or ""),
                str(row.get("transcript_id") or ""),
                0 if row.get("site_conservation") == "conserved" else 1,
                int(str(row.get("utr_start") or "0")),
                int(str(row.get("utr_end") or "0")),
                str(row.get("mirna") or ""),
            )
        )
        merged[query_gene] = merged_rows
    return merged

def build_summary_entry(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unique_mirnas = {
        str(row.get("mirna") or "").strip()
        for row in rows
        if row.get("mirna") not in {None, ""}
    }
    unique_transcripts = {
        str(row.get("transcript_id") or "").strip()
        for row in rows
        if row.get("transcript_id") not in {None, ""}
    }
    return {
        "mirna_count": len(unique_mirnas),
        "transcript_count": len(unique_transcripts),
        "row_count": len(rows),
        "conserved_row_count": sum(1 for row in rows if row.get("site_conservation") == "conserved"),
        "nonconserved_row_count": sum(1 for row in rows if row.get("site_conservation") == "nonconserved"),
        "transcripts": sorted(unique_transcripts),
    }

def annotate_rows_with_query_counts(rows: list[dict[str, Any]], summary_entry: dict[str, Any]) -> None:
    for row in rows:
        row["query_transcript_count"] = summary_entry["transcript_count"]
        row["query_mirna_count"] = summary_entry["mirna_count"]
        row["query_site_count"] = summary_entry["row_count"]

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    genes = load_genes(args)
    if not genes:
        print("No gene inputs were provided.", file=sys.stderr)
        return 2

    try:
        layout = build_output_layout(args=args, genes=genes)
    except TargetScanError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    local_mode_size_checks: dict[str, dict[str, Any]] = {}

    try:
        archive_paths = ensure_required_archives(
            args.cache_dir,
            local_mode=args.local_mode,
            local_data_dir=args.local_data_dir,
        )
        if args.local_mode:
            local_mode_size_checks = compare_local_mode_archives_to_remote(archive_paths)
        mirna_family_lookup = load_mirna_family_lookup(archive_paths["mir_family_info"])
        conserved_family_info = collect_family_info_for_queries(
            archive_paths["conserved_family_info"],
            member_name=ARCHIVE_SPECS["conserved_family_info"]["member"],
            query_genes=genes,
        )
        nonconserved_family_info = collect_family_info_for_queries(
            archive_paths["nonconserved_family_info"],
            member_name=ARCHIVE_SPECS["nonconserved_family_info"]["member"],
            query_genes=genes,
        )
        conserved_rows = collect_score_rows_for_queries(
            archive_paths["conserved_scores"],
            member_name=ARCHIVE_SPECS["conserved_scores"]["member"],
            query_genes=genes,
            site_conservation="conserved",
            mirna_family_lookup=mirna_family_lookup,
            family_info_by_query=conserved_family_info,
        )
        nonconserved_rows = collect_score_rows_for_queries(
            archive_paths["nonconserved_scores"],
            member_name=ARCHIVE_SPECS["nonconserved_scores"]["member"],
            query_genes=genes,
            site_conservation="nonconserved",
            mirna_family_lookup=mirna_family_lookup,
            family_info_by_query=nonconserved_family_info,
        )
        rows_by_query = merge_rows_by_query(
            query_genes=genes,
            conserved_rows=conserved_rows,
            nonconserved_rows=nonconserved_rows,
        )
    except TargetScanError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    temp_dir = layout["temp_dir"] if isinstance(layout["temp_dir"], Path) else None
    input_artifacts = copy_input_artifacts(args=args, genes=genes, temp_dir=temp_dir)

    all_rows: list[dict[str, Any]] = []
    summary_entries: dict[str, Any] = {}
    failures: dict[str, str] = {}
    unmatched_query_genes: list[str] = []

    for index, query_gene in enumerate(genes, start=1):
        rows = rows_by_query.get(query_gene, [])
        summary_entry = build_summary_entry(rows)
        summary_entries[query_gene] = summary_entry
        annotate_rows_with_query_counts(rows, summary_entry)
        all_rows.extend(rows)

        if rows:
            print(
                f"[{index}/{len(genes)}] {query_gene}: {summary_entry['mirna_count']} mature miRNAs across {summary_entry['row_count']} predicted sites",
                file=sys.stderr,
            )
            continue

        unmatched_query_genes.append(query_gene)
        failures[query_gene] = (
            "Gene symbol was not found in human TargetScanHuman mature-miRNA predicted target details."
        )
        print(f"[{index}/{len(genes)}] {query_gene}: no human TargetScan match", file=sys.stderr)

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
                "input_gene_count": len(genes),
                "matched_gene_count": len(genes) - len(unmatched_query_genes),
                "unmatched_query_genes": unmatched_query_genes,
                "result_row_count": len(all_rows),
                "input_artifacts": input_artifacts,
                "cache_files": {name: str(path) for name, path in archive_paths.items()},
                "local_mode": args.local_mode,
                "local_data_dir": str(args.local_data_dir),
                "archive_sources": {
                    name: (
                        "local_data"
                        if args.local_mode and name in LOCAL_ONLY_ARCHIVE_KEYS
                        else "cache_or_download"
                    )
                    for name in archive_paths
                },
                "local_mode_size_checks": local_mode_size_checks,
            },
            "results": summary_entries,
        },
    )
    if failures:
        write_json(errors_path, failures)
    elif errors_path.exists():
        errors_path.unlink()

    print(f"Wrote {len(all_rows)} TargetScan rows to {master_csv_path}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
