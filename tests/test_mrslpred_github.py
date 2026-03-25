from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.github_com.raghavagps_mrslpred.common.figure import (  # noqa: E402
    load_result_rows,
    render_localization_figure,
)
from webpages.github_com.raghavagps_mrslpred.common.runtime import (  # noqa: E402
    build_runtime_command,
    combine_prediction_rows,
    parse_fasta_records,
    resolve_runtime_command,
)
from webpages.github_com.raghavagps_mrslpred.manifest import COMMANDS_DOC, PAGE_METADATA, README_DOC, TASKS  # noqa: E402
from webpages.github_com.raghavagps_mrslpred.tasks.fasta_to_localization_bundle import (  # noqa: E402
    TASK_KEY as BUNDLE_TASK_KEY,
    build_output_layout as build_bundle_output_layout,
    main as bundle_main,
)


FASTA_FIXTURE = """>NM_006218.4 gene_symbol=PIK3CA query_gene_symbol=PIK3CA source=NCBI
ATGCATGCATGC
>NM_000211.5 gene_symbol=ITGB2 query_gene_symbol=ITGB2 source=NCBI
TTGGCCAATTGG
"""

RESULT_CSV_FIXTURE = """sequence_id,transcript_accession_version,transcript_accession,query_gene_symbol,gene_symbol,ribosome_label,cytosol_label,er_label,membrane_label,nucleus_label,exosome_label,ribosome_score,cytosol_score,er_score,membrane_score,nucleus_score,exosome_score,predicted_locations,predicted_location_count,fasta_header
NM_006218.4,NM_006218.4,NM_006218,PIK3CA,PIK3CA,No,Yes,Yes,Yes,Yes,Yes,0.2,0.3,0.4,0.5,0.6,0.7,Cytosol;ER;Membrane;Nucleus;Exosome,5,NM_006218.4 gene_symbol=PIK3CA query_gene_symbol=PIK3CA source=NCBI
"""


def test_manifest_exposes_bundle_metadata() -> None:
    bundle_task = TASKS[BUNDLE_TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://github.com/raghavagps/mrslpred"
    assert PAGE_METADATA["interaction_mode"] == "local_runtime"
    assert Path(bundle_task["entrypoint_script"]).exists()
    assert bundle_task["protocol_check_required"] is True
    assert "mrslpred_result.csv" in bundle_task["required_output_files"]
    assert "mrslpred_localization_figure.png" in bundle_task["required_output_files"]
    assert "mrslpred_localization_figure.pdf" in bundle_task["required_output_files"]


def test_top_level_docs_reference_bundle_only_contract() -> None:
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")
    assert "FASTA -> prediction result + figure bundle (mRSLPred GitHub)" in task_index
    assert "fasta_to_localization_bundle" in readme
    assert "fasta_to_localization_bundle" in commands


def test_runtime_helpers_work(tmp_path: Path) -> None:
    fasta_path = tmp_path / "sequences.fasta"
    fasta_path.write_text(FASTA_FIXTURE, encoding="utf-8")
    records = parse_fasta_records(fasta_path)
    assert records[0]["sequence_id"] == "NM_006218.4"
    args = SimpleNamespace(runtime_python=None, conda_env_name="mrslpred_py37", th1=0.1, th2=0.2, th3=0.3, th4=0.4, th5=0.5, th6=0.6)
    command = build_runtime_command(args, tmp_path / "mrslpred_motif.py", fasta_path, tmp_path / "official_output")
    resolved, label = resolve_runtime_command(command)
    assert resolved[:4] == ["conda", "run", "-n", "mrslpred_py37"]
    assert label == "conda:mrslpred_py37"


def test_combine_prediction_rows_and_figure_helpers_work(tmp_path: Path) -> None:
    rows, unmatched = combine_prediction_rows(
        fasta_records=[{"sequence_id": "NM_006218.4", "transcript_accession_version": "NM_006218.4", "transcript_accession": "NM_006218", "query_gene_symbol": "PIK3CA", "gene_symbol": "PIK3CA", "fasta_header": "NM_006218.4 gene_symbol=PIK3CA query_gene_symbol=PIK3CA source=NCBI"}],
        label_rows=[{"Seq ID": "NM_006218.4", "Ribosome": "Yes", "Cytosol": "No", "ER": "Yes", "Membrane": "No", "Nucleus": "Yes", "Exosome": "No"}],
        prob_rows=[{"Seq ID": "NM_006218.4", "Ribosome": "0.91", "Cytosol": "0.10", "ER": "0.81", "Membrane": "0.02", "Nucleus": "0.74", "Exosome": "0.11"}],
    )
    assert unmatched == []
    assert rows[0]["predicted_locations"] == "Ribosome;ER;Nucleus"
    csv_path = tmp_path / "result.csv"
    csv_path.write_text(RESULT_CSV_FIXTURE, encoding="utf-8")
    loaded_rows = load_result_rows(csv_path)
    output_path = tmp_path / "localization_figure.png"
    render_info = render_localization_figure(rows=loaded_rows, output_path=output_path, title="mRNA subcellular localization prediction (MRSLpred)")
    assert output_path.exists()
    assert render_info["column_count"] == 6


def test_bundle_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    args = SimpleNamespace(input=tmp_path / "sequences.fasta", input_dir=None, job_dir=tmp_path / "mrslpred_bundle_job", job_name=None, output_prefix=None)
    layout = build_bundle_output_layout(args=args, input_fasta=tmp_path / "sequences.fasta")
    assert layout["job_dir"] == tmp_path / "mrslpred_bundle_job"
    assert layout["figure_pdf_path"] == tmp_path / "mrslpred_bundle_job" / "mrslpred_localization_figure.pdf"


def test_input_dir_resolution_accepts_new_ncbi_fasta_name(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "ncbi_bundle"
    bundle_dir.mkdir()
    fasta_path = bundle_dir / "recommended_transcripts.fasta"
    fasta_path.write_text(FASTA_FIXTURE, encoding="utf-8")
    result = bundle_main(["--input-dir", str(bundle_dir)])
    assert result == 2


def test_bundle_main_requires_protocol_check_file(tmp_path: Path) -> None:
    fasta_path = tmp_path / "sequences.fasta"
    fasta_path.write_text(FASTA_FIXTURE, encoding="utf-8")
    assert bundle_main(["--input", str(fasta_path)]) == 2


def test_bundle_main_writes_result_png_pdf_and_summary(tmp_path: Path, monkeypatch) -> None:
    input_fasta = tmp_path / "sequences.fasta"
    input_fasta.write_text(FASTA_FIXTURE, encoding="utf-8")
    job_dir = tmp_path / "mrslpred_bundle_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="github_com.raghavagps_mrslpred",
        task_key="fasta_to_localization_bundle",
        mirna_count=None,
        query_count=None,
        input_file=input_fasta,
        execution_mode="delegated_subagent",
        subagent_name="MrslpredBundleWorker",
        current_boundary="This turn only validates the one-step mRSLPred bundle path and does not rerun upstream NCBI preparation.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_ensure_runtime_assets(cache_dir: Path):
        runtime_root = tmp_path / "runtime"
        script_path = runtime_root / "mrslpred_motif.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("# fake", encoding="utf-8")
        return {"runtime_root": runtime_root, "script_path": script_path, "data_dir": runtime_root / "Data", "motifs_dir": runtime_root / "motifs"}

    def fake_run_mrslpred(*, command: list[str], working_directory: Path):
        output_dir = job_dir / "temp" / "official_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "final_prediction.csv").write_text(
            "Seq ID,Ribosome,Cytosol,ER,Membrane,Nucleus,Exosome\nNM_006218.4,Yes,No,Yes,No,Yes,No\nNM_000211.5,No,Yes,No,Yes,No,No\n",
            encoding="utf-8",
        )
        (output_dir / "final_prob_prediction.csv").write_text(
            "Seq ID,Ribosome,Cytosol,ER,Membrane,Nucleus,Exosome\nNM_006218.4,0.91,0.10,0.81,0.02,0.74,0.11\nNM_000211.5,0.08,0.72,0.10,0.66,0.09,0.15\n",
            encoding="utf-8",
        )

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr("webpages.github_com.raghavagps_mrslpred.tasks.fasta_to_localization_bundle.ensure_runtime_assets", fake_ensure_runtime_assets)
    monkeypatch.setattr("webpages.github_com.raghavagps_mrslpred.tasks.fasta_to_localization_bundle.run_mrslpred", fake_run_mrslpred)

    result = bundle_main(["--input", str(input_fasta), "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 0
    assert (job_dir / "mrslpred_result.csv").exists()
    assert (job_dir / "mrslpred_localization_figure.png").exists()
    assert (job_dir / "mrslpred_localization_figure.pdf").exists()
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["figure_pdf_path"].endswith("mrslpred_localization_figure.pdf")
