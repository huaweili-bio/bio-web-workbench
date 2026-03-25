from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.cello_life_nctu_edu_tw.root.common.core import normalize_sequence_for_seqtype  # noqa: E402
from webpages.cello_life_nctu_edu_tw.root.common.core import parse_prediction_html as parse_cello_prediction_html  # noqa: E402
from webpages.cello_life_nctu_edu_tw.root.manifest import TASKS as CELLO_TASKS  # noqa: E402
from webpages.cello_life_nctu_edu_tw.root.tasks.protein_fasta_to_localization import main as cello_main  # noqa: E402
from webpages.cello_life_nctu_edu_tw.root.common.core import CelloError  # noqa: E402
from webpages.csbio_sjtu_edu_cn.cell_ploc_2.common.core import parse_prediction_html as parse_cell_ploc_prediction_html  # noqa: E402
from webpages.csbio_sjtu_edu_cn.cell_ploc_2.manifest import TASKS as CELL_PLOC_TASKS  # noqa: E402
from webpages.csbio_sjtu_edu_cn.cell_ploc_2.tasks.human_protein_fasta_to_localization import main as cell_ploc_main  # noqa: E402
from webpages.csbio_sjtu_edu_cn.cell_ploc_2.common.core import CellPlocError  # noqa: E402
from webpages.ncbi_nlm_nih_gov.protein.common.gene_resolution import flatten_product_report  # noqa: E402
from webpages.ncbi_nlm_nih_gov.protein.manifest import TASKS as NCBI_PROTEIN_TASKS  # noqa: E402
from webpages.ncbi_nlm_nih_gov.protein.tasks.gene_set_to_protein_bundle import main as ncbi_protein_main  # noqa: E402
from webpages.uniprot_org.uniprotkb.manifest import TASKS as UNIPROT_TASKS  # noqa: E402
from webpages.uniprot_org.uniprotkb.tasks.protein_accession_to_localization_annotation import main as uniprot_main  # noqa: E402
from webpages.uniprot_org.uniprotkb.common.api import UniProtError  # noqa: E402


CELL_PLOC_HTML = """
<html><body>
<tr><td><font size=4pt>Query protein</font></td><td><font size=4pt> Predicted location(s) </font></td></tr>
<tr align=center><td><font size=4pt>demo</font></td><td><strong><font size=4pt color='#5712A3'>Extracell. Mitochondrion. </font></strong></td></tr>
</body></html>
"""

CELLO_HTML = """
<html><body>
<div>Prediction result</div>
<div>Predicted location(s): Cytoplasm, Nucleus</div>
</body></html>
"""

CELLO_RESULTS_HTML = """
<head><title>CELLO predictive system</title></head>
<div align=center>
<h2><a href=temp/demo.result_save.txt target="_blank">CELLO RESULTS</a></h2>
<table border=0 cellpadding=0 cellspacing=0>
<tr><td><br>CELLO Prediction:</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;&nbsp;&nbsp;&nbsp;Nuclear</td><td>&nbsp;&nbsp;&nbsp;&nbsp;1.515&nbsp;&nbsp;*</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;&nbsp;&nbsp;&nbsp;Mitochondrial</td><td>&nbsp;&nbsp;&nbsp;&nbsp;1.169&nbsp;&nbsp;*</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;&nbsp;&nbsp;&nbsp;Extracellular</td><td>&nbsp;&nbsp;&nbsp;&nbsp;0.749</td></tr>
<tr><td COLSPAN=4><br>*********************************************************************************<br><br></td></tr>
</table>
</div>
"""


def test_task_index_mentions_new_protein_localization_methods() -> None:
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")
    assert "Gene set -> recommended-protein FASTA bundle (NCBI)" in task_index
    assert "Protein accession -> localization annotation (UniProtKB)" in task_index
    assert "Protein FASTA -> localization prediction (CELLO)" in task_index
    assert "Human protein FASTA -> localization prediction (Cell-PLoc 2.0)" in task_index


def test_manifests_expose_new_task_metadata() -> None:
    assert "gene_set_to_protein_bundle" in NCBI_PROTEIN_TASKS
    assert "protein_accession_to_localization_annotation" in UNIPROT_TASKS
    assert "protein_fasta_to_localization" in CELLO_TASKS
    assert "human_protein_fasta_to_localization" in CELL_PLOC_TASKS


def test_ncbi_protein_flattening_keeps_recommended_row() -> None:
    product = {
        "gene_id": 7157,
        "symbol": "TP53",
        "description": "tumor protein p53",
        "tax_id": 9606,
        "taxname": "Homo sapiens",
        "type": "protein-coding",
        "transcripts": [
            {
                "accession_version": "NM_000546.6",
                "name": "transcript 1",
                "length": 2500,
                "type": "mRNA",
                "select_category": "MANE_SELECT",
                "protein": {
                    "accession_version": "NP_000537.3",
                    "name": "cellular tumor antigen p53",
                    "length": 393,
                },
            },
            {
                "accession_version": "XM_123456.1",
                "name": "transcript 2",
                "length": 1000,
                "type": "mRNA",
                "select_category": "",
                "protein": {
                    "accession_version": "XP_123456.1",
                    "name": "alt isoform",
                    "length": 200,
                },
            },
        ],
    }
    rows = flatten_product_report("TP53", product)
    assert rows[0]["protein_accession_version"] == "NP_000537.3"
    assert rows[0]["protein_is_recommended"] == 1


def test_uniprot_task_writes_annotation_table(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "uniprot_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="uniprot_org.uniprotkb",
        task_key="protein_accession_to_localization_annotation",
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the one-step UniProtKB localization annotation path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def fetch_annotation_rows(self, accession: str, *, gene_symbol: str = "", organism_id: str = ""):
            return (
                "https://rest.uniprot.org/example",
                [
                    {
                        "Entry": "P04637",
                        "Entry Name": "P53_HUMAN",
                        "Gene Names": "TP53",
                        "Protein names": "Cellular tumor antigen p53",
                        "Annotation Score": "5 out of 5",
                        "Reviewed": "reviewed",
                        "Subcellular location [CC]": "Nucleus.",
                    }
                ],
            )

    monkeypatch.setattr("webpages.uniprot_org.uniprotkb.tasks.protein_accession_to_localization_annotation.UniProtClient", FakeClient)
    result = uniprot_main(["--accession", "P04637", "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 0
    assert (job_dir / "uniprot_subcellular_annotation.tsv").exists()
    assert "Nucleus." in (job_dir / "uniprot_subcellular_annotation.tsv").read_text(encoding="utf-8")


def test_uniprot_task_returns_error_when_all_accessions_fail(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "uniprot_job_failed"
    ticket_path = tmp_path / "protocol_check_failed.json"
    payload = create_protocol_ticket(
        page_key="uniprot_org.uniprotkb",
        task_key="protein_accession_to_localization_annotation",
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the failed UniProtKB localization annotation path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def fetch_annotation_rows(self, accession: str, *, gene_symbol: str = "", organism_id: str = ""):
            raise UniProtError(f"Bad accession: {accession}")

    monkeypatch.setattr("webpages.uniprot_org.uniprotkb.tasks.protein_accession_to_localization_annotation.UniProtClient", FakeClient)
    result = uniprot_main(["--accession", "BAD123", "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 1
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["result_status"] == "failed"
    assert (job_dir / "temp" / "errors.json").exists()


def test_cello_parser_and_task(tmp_path: Path, monkeypatch) -> None:
    assert parse_cello_prediction_html(CELLO_HTML) == ["Cytoplasm", "Nucleus"]
    assert parse_cello_prediction_html(CELLO_RESULTS_HTML) == ["Nuclear", "Mitochondrial"]
    assert normalize_sequence_for_seqtype("AUGCUU", "dna") == "ATGCTT"
    fasta_path = tmp_path / "protein.fasta"
    fasta_path.write_text(">demo\nMGLSDGEWQLVLNVWGKVEADIPGHGQEVLIRLFKGHPETLEKFDKFKHLKTEAEMKASED\n", encoding="utf-8")
    job_dir = tmp_path / "cello_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="cello_life_nctu_edu_tw.root",
        task_key="protein_fasta_to_localization",
        query_count=None,
        input_file=fasta_path,
        execution_mode="delegated_subagent",
        subagent_name="CelloWorker",
        current_boundary="This turn only validates the one-step CELLO prediction path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr("webpages.cello_life_nctu_edu_tw.root.tasks.protein_fasta_to_localization.submit_query", lambda **_: CELLO_HTML)
    result = cello_main(["--input", str(fasta_path), "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 0
    assert "CELLO" in (job_dir / "protein_localization_result.csv").read_text(encoding="utf-8")


def test_cello_task_returns_error_when_all_sequences_fail(tmp_path: Path, monkeypatch) -> None:
    fasta_path = tmp_path / "protein_fail.fasta"
    fasta_path.write_text(">demo\nMGLSDGEWQLVLNVWGKVEADIPGHGQEVLIRLFKGHPETLEKFDKFKHLKTEAEMKASED\n", encoding="utf-8")
    job_dir = tmp_path / "cello_job_failed"
    ticket_path = tmp_path / "protocol_check_failed.json"
    payload = create_protocol_ticket(
        page_key="cello_life_nctu_edu_tw.root",
        task_key="protein_fasta_to_localization",
        query_count=None,
        input_file=fasta_path,
        execution_mode="delegated_subagent",
        subagent_name="CelloWorker",
        current_boundary="This turn only validates the failed CELLO prediction path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _raise_error(**_: object) -> str:
        raise CelloError("HTTP 500")

    monkeypatch.setattr("webpages.cello_life_nctu_edu_tw.root.tasks.protein_fasta_to_localization.submit_query", _raise_error)
    result = cello_main(["--input", str(fasta_path), "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 1
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["result_status"] == "failed"
    assert (job_dir / "temp" / "errors.json").exists()


def test_cell_ploc_parser_and_task(tmp_path: Path, monkeypatch) -> None:
    assert parse_cell_ploc_prediction_html(CELL_PLOC_HTML) == ["Extracell", "Mitochondrion"]
    fasta_path = tmp_path / "protein.fasta"
    fasta_path.write_text(">demo\nMGLSDGEWQLVLNVWGKVEADIPGHGQEVLIRLFKGHPETLEKFDKFKHLKTEAEMKASED\n", encoding="utf-8")
    job_dir = tmp_path / "cell_ploc_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="csbio_sjtu_edu_cn.cell_ploc_2",
        task_key="human_protein_fasta_to_localization",
        query_count=None,
        input_file=fasta_path,
        execution_mode="delegated_subagent",
        subagent_name="CellPlocWorker",
        current_boundary="This turn only validates the one-step Cell-PLoc prediction path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr("webpages.csbio_sjtu_edu_cn.cell_ploc_2.tasks.human_protein_fasta_to_localization.submit_query", lambda **_: CELL_PLOC_HTML)
    result = cell_ploc_main(["--input", str(fasta_path), "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 0
    assert "Cell-PLoc 2.0" in (job_dir / "protein_localization_result.csv").read_text(encoding="utf-8")


def test_cell_ploc_task_returns_error_when_all_sequences_fail(tmp_path: Path, monkeypatch) -> None:
    fasta_path = tmp_path / "protein_fail.fasta"
    fasta_path.write_text(">demo\nMGLSDGEWQLVLNVWGKVEADIPGHGQEVLIRLFKGHPETLEKFDKFKHLKTEAEMKASED\n", encoding="utf-8")
    job_dir = tmp_path / "cell_ploc_job_failed"
    ticket_path = tmp_path / "protocol_check_failed.json"
    payload = create_protocol_ticket(
        page_key="csbio_sjtu_edu_cn.cell_ploc_2",
        task_key="human_protein_fasta_to_localization",
        query_count=None,
        input_file=fasta_path,
        execution_mode="delegated_subagent",
        subagent_name="CellPlocWorker",
        current_boundary="This turn only validates the failed Cell-PLoc prediction path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _raise_error(**_: object) -> str:
        raise CellPlocError("HTTP 500")

    monkeypatch.setattr("webpages.csbio_sjtu_edu_cn.cell_ploc_2.tasks.human_protein_fasta_to_localization.submit_query", _raise_error)
    result = cell_ploc_main(["--input", str(fasta_path), "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 1
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["result_status"] == "failed"
    assert (job_dir / "temp" / "errors.json").exists()


def test_ncbi_protein_task_writes_bundle_outputs(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "ncbi_protein_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="ncbi_nlm_nih_gov.protein",
        task_key="gene_set_to_protein_bundle",
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the one-step NCBI protein bundle path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    class FakeProteinClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def fetch_product_report(self, gene_symbol: str, taxon: str):
            return (
                "https://api.ncbi.nlm.nih.gov/example",
                {
                    "reports": [
                        {
                            "product": {
                                "gene_id": 7157,
                                "symbol": gene_symbol,
                                "description": "tumor protein p53",
                                "tax_id": 9606,
                                "taxname": taxon,
                                "type": "protein-coding",
                                "transcripts": [
                                    {
                                        "accession_version": "NM_000546.6",
                                        "name": "transcript 1",
                                        "length": 2500,
                                        "type": "mRNA",
                                        "select_category": "MANE_SELECT",
                                        "protein": {
                                            "accession_version": "NP_000537.3",
                                            "name": "cellular tumor antigen p53",
                                            "length": 393,
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            )

    class FakeFastaClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def fetch_fasta_text(self, accession: str):
            return (
                "https://eutils.ncbi.nlm.nih.gov/example",
                ">NP_000537.3 cellular tumor antigen p53\nMEEPQSDPSV\n",
            )

    monkeypatch.setattr("webpages.ncbi_nlm_nih_gov.protein.tasks.gene_set_to_protein_bundle.NcbiProteinClient", FakeProteinClient)
    monkeypatch.setattr("webpages.ncbi_nlm_nih_gov.protein.tasks.gene_set_to_protein_bundle.NcbiProteinFastaClient", FakeFastaClient)
    result = ncbi_protein_main(["--gene", "TP53", "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 0
    assert (job_dir / "recommended_proteins.csv").exists()
    assert (job_dir / "recommended_proteins.fasta").exists()
    assert (job_dir / "temp" / "matched_gene_summary.csv").exists()
    assert (job_dir / "temp" / "all_proteins.csv").exists()
