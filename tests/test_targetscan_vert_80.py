from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.targetscan_org.vert_80.manifest import (  # noqa: E402
    COMMANDS_DOC,
    PAGE_METADATA,
    README_DOC,
    TASKS,
)
from webpages.targetscan_org.vert_80.tasks.mrna_to_mirna import (  # noqa: E402
    ARCHIVE_SPECS,
    TASK_KEY,
    TASK_METADATA,
    TargetScanError,
    annotate_rows_with_query_counts,
    build_output_layout,
    build_summary_entry,
    compare_local_mode_archives_to_remote,
    collect_family_info_for_queries,
    collect_score_rows_for_queries,
    ensure_required_archives,
    fetch_remote_content_length,
    load_genes,
    load_mirna_family_lookup,
    main,
    merge_rows_by_query,
    split_arg_values,
)


MIR_FAMILY_FIXTURE = """miR family\tSeed+m8\tSpecies ID\tMiRBase ID\tMature sequence\tFamily Conservation?\tMiRBase Accession
miR-29\tUAGCACCA\t9606\thsa-miR-29-3p\tTAGCACCATTTGAAATCGGTT\t2\tMIMAT0000086
miR-19\tAAUGCAAA\t9606\thsa-miR-19a-3p\tUGUGCAAAUCUAUGCAAAACUGA\t2\tMIMAT0000073
miR-16\tGCAGCAUU\t9606\thsa-miR-16-5p\tUAGCAGCACGUAAAUAUUGGCG\t2\tMIMAT0000069
miR-29\tUAGCACCA\t10090\tmmu-miR-29-3p\tTAGCACCATCTGAAATCGGTT\t2\tMIMAT0000123
"""

CONSERVED_FAMILY_INFO_FIXTURE = """miR Family\tGene ID\tGene Symbol\tTranscript ID\tSpecies ID\tUTR start\tUTR end\tMSA start\tMSA end\tSeed match\tPCT
miR-29\tENSGAPP\tAPP\tENSTAPP001\t9606\t43\t49\t100\t106\t7mer-m8\t0.52
miR-16\tENSGAPP\tAPP\tENSTAPP001\t9606\t88\t94\t145\t151\t7mer-1A\t0.33
miR-29\tENSGMOUSE\tAPP\tENSTMOUSE001\t10090\t43\t49\t100\t106\t7mer-m8\t0.52
"""

NONCONSERVED_FAMILY_INFO_FIXTURE = """miR Family\tGene ID\tGene Symbol\tTranscript ID\tSpecies ID\tUTR start\tUTR end\tMSA start\tMSA end\tSeed match\tPCT
miR-19\tENSGAPP\tAPP\tENSTAPP001\t9606\t120\t127\t0\t0\t8mer\t
"""

CONSERVED_SCORE_FIXTURE = """Gene ID\tGene Symbol\tTranscript ID\tGene Tax ID\tmiRNA\tSite Type\tUTR_start\tUTR end\tcontext++ score\tcontext++ score percentile\tweighted context++ score\tweighted context++ score percentile\tPredicted relative KD
ENSGAPP\tAPP\tENSTAPP001\t9606\thsa-miR-29-3p\t2\t43\t49\t-0.260\t92\t-0.260\t94\t-4.8556
ENSGAPP\tAPP\tENSTAPP001\t9606\thsa-miR-16-5p\t1\t88\t94\t-0.150\t85\t-0.120\t82\t-4.1000
ENSGBDNF\tBDNF\tENSTBDNF001\t9606\thsa-miR-29-3p\t2\t60\t66\t-0.200\t80\t-0.180\t79\t-3.2000
ENSGAPP\tAPP\tENSTMOUSE001\t10090\thsa-miR-29-3p\t2\t43\t49\t-0.260\t92\t-0.260\t94\t-4.8556
"""

NONCONSERVED_SCORE_FIXTURE = """Gene ID\tGene Symbol\tTranscript ID\tGene Tax ID\tmiRNA\tSite Type\tUTR_start\tUTR end\tcontext++ score\tcontext++ score percentile\tweighted context++ score\tweighted context++ score percentile\tPredicted relative KD
ENSGAPP\tAPP\tENSTAPP001\t9606\thsa-miR-19a-3p\t3\t120\t127\t-0.310\t95\t-0.310\t95\t-4.0770
ENSGAPP\tAPP\tENSTAPP001\t9606\thsa-miR-29-3p\t-2\t150\t156\t-0.100\t60\t-0.080\t59\t-2.5000
"""


def write_zip(path: Path, member: str, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        archive.writestr(member, content)
    return path


def build_archive_fixture_set(base_dir: Path) -> dict[str, Path]:
    return {
        "mir_family_info": write_zip(
            base_dir / "miR_Family_Info.txt.zip",
            ARCHIVE_SPECS["mir_family_info"]["member"],
            MIR_FAMILY_FIXTURE,
        ),
        "conserved_family_info": write_zip(
            base_dir / "Conserved_Family_Info.txt.zip",
            ARCHIVE_SPECS["conserved_family_info"]["member"],
            CONSERVED_FAMILY_INFO_FIXTURE,
        ),
        "nonconserved_family_info": write_zip(
            base_dir / "Nonconserved_Family_Info.txt.zip",
            ARCHIVE_SPECS["nonconserved_family_info"]["member"],
            NONCONSERVED_FAMILY_INFO_FIXTURE,
        ),
        "conserved_scores": write_zip(
            base_dir / "Conserved_Site_Context_Scores.txt.zip",
            ARCHIVE_SPECS["conserved_scores"]["member"],
            CONSERVED_SCORE_FIXTURE,
        ),
        "nonconserved_scores": write_zip(
            base_dir / "Nonconserved_Site_Context_Scores.txt.zip",
            ARCHIVE_SPECS["nonconserved_scores"]["member"],
            NONCONSERVED_SCORE_FIXTURE,
        ),
    }


def test_manifest_exposes_page_and_task_metadata() -> None:
    task_entry = TASKS[TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://www.targetscan.org/vert_80/"
    assert PAGE_METADATA["interaction_mode"] == "download_table"
    assert Path(task_entry["entrypoint_script"]).exists()
    assert Path(PAGE_METADATA["readme"]).exists()
    assert Path(PAGE_METADATA["commands_doc"]).exists()
    assert task_entry["preferred_output_mode"] == "job_dir"
    assert task_entry["master_file_name"] == "targetscanhuman_result.csv"
    assert task_entry["master_file_is_concatenated"] is False
    assert task_entry["protocol_check_required"] is True
    assert "query_mirna_count" in task_entry["master_file_required_columns"]


def test_top_level_docs_reference_targetscan_structure_and_boundaries() -> None:
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")

    assert "webpages\\targetscan_org\\vert_80" in task_index
    assert "mrna_to_mirna.py" in task_index
    assert "mature miRNA" in task_index


def test_page_docs_cover_output_contract_and_cache_boundary() -> None:
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")
    task_entry = TASKS[TASK_KEY]

    assert "Current task" in readme
    assert "mature miRNA predicted target details" in readme
    assert "Nonconserved_Site_Context_Scores.txt.zip" in readme
    assert "## help" in commands
    assert "## smoke" in commands
    assert "## task" in commands
    assert "## debug" in commands
    assert "## long-running" in commands
    assert "multiple official ZIP files" in commands
    assert "protocol_gate.py" in commands
    assert "--query-count" in commands
    assert task_entry["smoke_command"] in commands


def test_split_arg_values_accepts_comma_separated_inputs() -> None:
    assert split_arg_values(["APP, BDNF", "MAPT"]) == ["APP", "BDNF", "MAPT"]


def test_load_genes_supports_text_csv_and_casefolded_dedup(tmp_path: Path) -> None:
    text_input = tmp_path / "genes.txt"
    text_input.write_text("# comment\nAPP\nbdnf, APP\n", encoding="utf-8")
    csv_input = tmp_path / "genes.csv"
    csv_input.write_text("gene_symbol\nAPP\nMAPT\n", encoding="utf-8")

    class Args:
        gene = ["app", "GFAP"]
        input = text_input

    assert load_genes(Args()) == ["app", "GFAP", "bdnf"]

    class CsvArgs:
        gene = []
        input = csv_input

    assert load_genes(CsvArgs()) == ["APP", "MAPT"]


def test_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    class Args:
        job_dir = tmp_path / "targetscan_job"
        job_name = None
        output_prefix = None
        input = tmp_path / "input.csv"

    layout = build_output_layout(args=Args(), genes=["APP"])
    assert layout["mode"] == "job_dir"
    assert layout["job_dir"] == tmp_path / "targetscan_job"
    assert layout["master_csv_path"] == tmp_path / "targetscan_job" / "targetscanhuman_result.csv"
    assert layout["summary_path"] == tmp_path / "targetscan_job" / "temp" / "summary.json"
    assert layout["errors_path"] == tmp_path / "targetscan_job" / "temp" / "errors.json"


def test_collect_rows_builds_mature_mirna_detail_rows(tmp_path: Path) -> None:
    archive_paths = build_archive_fixture_set(tmp_path)
    mirna_family_lookup = load_mirna_family_lookup(archive_paths["mir_family_info"])
    conserved_family_info = collect_family_info_for_queries(
        archive_paths["conserved_family_info"],
        member_name=ARCHIVE_SPECS["conserved_family_info"]["member"],
        query_genes=["app", "BDNF"],
    )
    nonconserved_family_info = collect_family_info_for_queries(
        archive_paths["nonconserved_family_info"],
        member_name=ARCHIVE_SPECS["nonconserved_family_info"]["member"],
        query_genes=["app", "BDNF"],
    )

    conserved_rows = collect_score_rows_for_queries(
        archive_paths["conserved_scores"],
        member_name=ARCHIVE_SPECS["conserved_scores"]["member"],
        query_genes=["app", "BDNF"],
        site_conservation="conserved",
        mirna_family_lookup=mirna_family_lookup,
        family_info_by_query=conserved_family_info,
    )
    nonconserved_rows = collect_score_rows_for_queries(
        archive_paths["nonconserved_scores"],
        member_name=ARCHIVE_SPECS["nonconserved_scores"]["member"],
        query_genes=["app", "BDNF"],
        site_conservation="nonconserved",
        mirna_family_lookup=mirna_family_lookup,
        family_info_by_query=nonconserved_family_info,
    )
    rows_by_query = merge_rows_by_query(
        query_genes=["app", "BDNF"],
        conserved_rows=conserved_rows,
        nonconserved_rows=nonconserved_rows,
    )

    assert TASK_METADATA["task_key"] == "mrna_to_mirna"
    assert TASK_METADATA["master_file_mode"] == "direct_generated_master_file"
    assert len(rows_by_query["app"]) == 4
    assert rows_by_query["app"][0]["mirna"] == "hsa-miR-29-3p"
    assert rows_by_query["app"][0]["seed_match"] == "7mer-m8"
    assert rows_by_query["app"][0]["pct"] == "0.52"
    assert rows_by_query["app"][-1]["site_conservation"] == "nonconserved"
    assert rows_by_query["app"][-1]["seed_match"] == "7mer-m8"
    summary = build_summary_entry(rows_by_query["app"])
    annotate_rows_with_query_counts(rows_by_query["app"], summary)
    assert summary["mirna_count"] == 3
    assert summary["transcript_count"] == 1
    assert all(row["query_mirna_count"] == 3 for row in rows_by_query["app"])


def test_main_requires_protocol_check_file() -> None:
    result = main(["--gene", "APP"])
    assert result == 2


def test_main_writes_results_and_errors_without_failing_for_unmatched(tmp_path: Path, monkeypatch) -> None:
    archive_paths = build_archive_fixture_set(tmp_path / "cache")
    job_dir = tmp_path / "targetscan_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="targetscan_org.vert_80",
        task_key="mrna_to_mirna",
        mirna_count=None,
        query_count=2,
        input_file=None,
        execution_mode="delegated_subagent",
        subagent_name="TargetScanWorker",
        current_boundary="This turn only validates the TargetScanHuman mature-miRNA detail path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr(
        "webpages.targetscan_org.vert_80.tasks.mrna_to_mirna.ensure_required_archives",
        lambda cache_dir, local_mode=False, local_data_dir=None: archive_paths,
    )

    result = main(
        [
            "--gene",
            "APP",
            "--gene",
            "NO_SUCH_GENE",
            "--job-dir",
            str(job_dir),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--protocol-check-file",
            str(ticket_path),
        ]
    )

    assert result == 0
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    errors = json.loads((job_dir / "temp" / "errors.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((job_dir / "targetscanhuman_result.csv").open("r", encoding="utf-8")))

    assert len(rows) == 4
    assert summary["_meta"]["unmatched_query_genes"] == ["NO_SUCH_GENE"]
    assert summary["results"]["APP"]["mirna_count"] == 3
    assert summary["results"]["NO_SUCH_GENE"]["mirna_count"] == 0
    assert "NO_SUCH_GENE" in errors


def test_ensure_required_archives_downloads_when_cache_is_missing(tmp_path: Path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"

    def fake_download(url: str, destination: Path, *, timeout: float = 120.0, max_retries: int = 4) -> None:
        filename = destination.name
        for spec in ARCHIVE_SPECS.values():
            if filename == spec["url"].rsplit("/", 1)[-1]:
                if "miR_Family_Info" in filename:
                    write_zip(destination, spec["member"], MIR_FAMILY_FIXTURE)
                elif "Conserved_Family_Info" in filename:
                    write_zip(destination, spec["member"], CONSERVED_FAMILY_INFO_FIXTURE)
                elif "Nonconserved_Family_Info" in filename:
                    write_zip(destination, spec["member"], NONCONSERVED_FAMILY_INFO_FIXTURE)
                elif "Conserved_Site_Context_Scores" in filename:
                    write_zip(destination, spec["member"], CONSERVED_SCORE_FIXTURE)
                elif "Nonconserved_Site_Context_Scores" in filename:
                    write_zip(destination, spec["member"], NONCONSERVED_SCORE_FIXTURE)
                return
        raise AssertionError(f"Unexpected download target: {filename}")

    monkeypatch.setattr(
        "webpages.targetscan_org.vert_80.tasks.mrna_to_mirna.download_with_retries",
        fake_download,
    )

    archive_paths = ensure_required_archives(cache_dir)
    assert sorted(archive_paths) == sorted(ARCHIVE_SPECS)
    assert all(path.exists() for path in archive_paths.values())


def test_ensure_required_archives_local_mode_uses_predownloaded_score_files(tmp_path: Path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    local_data_dir = tmp_path / "local_data"
    local_data_dir.mkdir(parents=True, exist_ok=True)
    write_zip(
        local_data_dir / "Conserved_Site_Context_Scores.txt.zip",
        ARCHIVE_SPECS["conserved_scores"]["member"],
        CONSERVED_SCORE_FIXTURE,
    )
    write_zip(
        local_data_dir / "Nonconserved_Site_Context_Scores.txt.zip",
        ARCHIVE_SPECS["nonconserved_scores"]["member"],
        NONCONSERVED_SCORE_FIXTURE,
    )

    def fake_download(url: str, destination: Path, *, timeout: float = 120.0, max_retries: int = 4) -> None:
        filename = destination.name
        for spec in ARCHIVE_SPECS.values():
            if filename == spec["url"].rsplit("/", 1)[-1]:
                if "miR_Family_Info" in filename:
                    write_zip(destination, spec["member"], MIR_FAMILY_FIXTURE)
                elif "Conserved_Family_Info" in filename:
                    write_zip(destination, spec["member"], CONSERVED_FAMILY_INFO_FIXTURE)
                elif "Nonconserved_Family_Info" in filename:
                    write_zip(destination, spec["member"], NONCONSERVED_FAMILY_INFO_FIXTURE)
                else:
                    raise AssertionError(f"Local mode should not download score archive {filename}")
                return
        raise AssertionError(f"Unexpected download target: {filename}")

    monkeypatch.setattr(
        "webpages.targetscan_org.vert_80.tasks.mrna_to_mirna.download_with_retries",
        fake_download,
    )

    archive_paths = ensure_required_archives(
        cache_dir,
        local_mode=True,
        local_data_dir=local_data_dir,
    )
    assert archive_paths["conserved_scores"] == local_data_dir / "Conserved_Site_Context_Scores.txt.zip"
    assert archive_paths["nonconserved_scores"] == local_data_dir / "Nonconserved_Site_Context_Scores.txt.zip"


def test_compare_local_mode_archives_to_remote_fails_when_remote_is_larger(tmp_path: Path, monkeypatch) -> None:
    archive_paths = build_archive_fixture_set(tmp_path / "cache")

    def fake_remote_size(url: str, *, timeout: float = 60.0) -> int:
        if url.endswith("Conserved_Site_Context_Scores.txt.zip"):
            return archive_paths["conserved_scores"].stat().st_size
        if url.endswith("Nonconserved_Site_Context_Scores.txt.zip"):
            return archive_paths["nonconserved_scores"].stat().st_size + 10
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "webpages.targetscan_org.vert_80.tasks.mrna_to_mirna.fetch_remote_content_length",
        fake_remote_size,
    )

    try:
        compare_local_mode_archives_to_remote(archive_paths)
    except TargetScanError as exc:
        assert "TargetScan may have updated" in str(exc)
    else:
        raise AssertionError("Expected remote-larger local-mode comparison to fail closed.")


def test_compare_local_mode_archives_to_remote_records_warning_when_remote_size_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    archive_paths = build_archive_fixture_set(tmp_path / "cache")

    def fake_remote_size(url: str, *, timeout: float = 60.0) -> int:
        if url.endswith("Conserved_Site_Context_Scores.txt.zip"):
            return archive_paths["conserved_scores"].stat().st_size
        raise TargetScanError("remote size query failed")

    monkeypatch.setattr(
        "webpages.targetscan_org.vert_80.tasks.mrna_to_mirna.fetch_remote_content_length",
        fake_remote_size,
    )

    checks = compare_local_mode_archives_to_remote(archive_paths)
    assert checks["conserved_scores"]["status"] == "match"
    assert checks["nonconserved_scores"]["status"] == "remote_size_unknown"
    assert "remote size query failed" in checks["nonconserved_scores"]["message"]


def test_main_returns_error_when_cache_download_fails(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "targetscan_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="targetscan_org.vert_80",
        task_key="mrna_to_mirna",
        mirna_count=None,
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the TargetScanHuman single-query path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fail_download(url: str, destination: Path, *, timeout: float = 120.0, max_retries: int = 4) -> None:
        raise TargetScanError("download exploded")

    monkeypatch.setattr(
        "webpages.targetscan_org.vert_80.tasks.mrna_to_mirna.download_with_retries",
        fail_download,
    )

    result = main(
        [
            "--gene",
            "APP",
            "--job-dir",
            str(job_dir),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--protocol-check-file",
            str(ticket_path),
        ]
    )

    assert result == 1
