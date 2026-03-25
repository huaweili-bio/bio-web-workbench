from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import ProtocolGateError, create_protocol_ticket, infer_input_type, validate_protocol_ticket  # noqa: E402
from webpages.diana_e_ce_uth_gr.lncbasev3_home.tasks.mirna_to_lncrna import main as lncbase_main  # noqa: E402
from webpages.github_com.raghavagps_mrslpred.tasks.fasta_to_localization_bundle import main as mrslpred_bundle_main  # noqa: E402
from webpages.mirdb_org.index.tasks.mrna_to_mirna import main as mirdb_main  # noqa: E402
from webpages.ncbi_nlm_nih_gov.gene.tasks.gene_set_to_fasta_bundle import main as ncbi_bundle_main  # noqa: E402
from webpages.ncbi_nlm_nih_gov.protein.tasks.gene_set_to_protein_bundle import main as ncbi_protein_main  # noqa: E402
from webpages.rnasysu_com.encori.tasks.mirna_to_lncrna import main as encori_main  # noqa: E402
from webpages.rnasysu_com.encori.tasks.mrna_to_mirna import main as encori_mrna_main  # noqa: E402
from webpages.uniprot_org.uniprotkb.tasks.protein_accession_to_localization_annotation import main as uniprot_main  # noqa: E402
from webpages.cello_life_nctu_edu_tw.root.tasks.protein_fasta_to_localization import main as cello_main  # noqa: E402
from webpages.csbio_sjtu_edu_cn.cell_ploc_2.tasks.human_protein_fasta_to_localization import main as cell_ploc_main  # noqa: E402
from webpages.rnalocate_org.search.tasks.rna_symbol_to_localization_annotation import main as rnalocate_main  # noqa: E402


def test_infer_input_type_distinguishes_single_and_batch_modes(tmp_path: Path) -> None:
    input_file = tmp_path / "queries.txt"
    input_file.write_text("a\n", encoding="utf-8")
    assert infer_input_type(mirna_count=1, input_file=None) == "single_inline"
    assert infer_input_type(query_count=2, input_file=None) == "batch_inline"
    assert infer_input_type(query_count=None, input_file=input_file) == "batch_file"


def test_protocol_gate_rejects_batch_main_thread_execution() -> None:
    try:
        create_protocol_ticket(
            page_key="rnasysu_com.encori",
            task_key="mirna_to_lncrna",
            mirna_count=5,
            input_file=None,
            execution_mode="main_thread",
            subagent_name="",
            current_boundary="This turn only runs ENCORI single-database querying.",
            job_dir=ROOT / "outputs" / "tasks" / "encori__demo",
        )
    except ProtocolGateError as exc:
        assert "must be delegated" in str(exc)
    else:
        raise AssertionError("Expected batch main-thread execution to be rejected.")


def test_protocol_ticket_supports_ncbi_bundle(tmp_path: Path) -> None:
    job_dir = tmp_path / "ncbi_bundle_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="ncbi_nlm_nih_gov.gene",
        task_key="gene_set_to_fasta_bundle",
        mirna_count=None,
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the one-step NCBI bundle path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    validated = validate_protocol_ticket(ticket_path, page_key="ncbi_nlm_nih_gov.gene", task_key="gene_set_to_fasta_bundle", input_type="single_inline", job_dir=job_dir)
    assert validated["query_count"] == 1


def test_protocol_ticket_supports_mrslpred_bundle_batch_file(tmp_path: Path) -> None:
    input_file = tmp_path / "sequences.fasta"
    input_file.write_text(">NM_006218.4 gene_symbol=PIK3CA query_gene_symbol=PIK3CA source=NCBI\nATGC\n", encoding="utf-8")
    job_dir = tmp_path / "mrslpred_bundle_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="github_com.raghavagps_mrslpred",
        task_key="fasta_to_localization_bundle",
        mirna_count=None,
        query_count=None,
        input_file=input_file,
        execution_mode="delegated_subagent",
        subagent_name="MrslpredBundleWorker",
        current_boundary="This turn only runs the one-step mRSLPred bundle.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    validated = validate_protocol_ticket(ticket_path, page_key="github_com.raghavagps_mrslpred", task_key="fasta_to_localization_bundle", input_type="batch_file", job_dir=job_dir)
    assert validated["execution_mode"] == "delegated_subagent"


def test_existing_other_tasks_still_require_protocol_check_file() -> None:
    assert lncbase_main(["--mirna", "hsa-miR-21-5p"]) == 2
    assert encori_main(["--mirna", "hsa-miR-21-5p"]) == 2
    assert encori_mrna_main(["--gene", "PIK3CA"]) == 2
    assert mirdb_main(["--gene", "PIK3CA"]) == 2


def test_bundle_tasks_require_protocol_check_file(tmp_path: Path) -> None:
    fasta_path = tmp_path / "sequences.fasta"
    fasta_path.write_text(">NM_006218.4 gene_symbol=PIK3CA query_gene_symbol=PIK3CA source=NCBI\nATGC\n", encoding="utf-8")
    assert ncbi_bundle_main(["--gene", "PIK3CA"]) == 2
    assert mrslpred_bundle_main(["--input", str(fasta_path)]) == 2


def test_new_protein_tasks_require_protocol_check_file(tmp_path: Path) -> None:
    fasta_path = tmp_path / "protein.fasta"
    fasta_path.write_text(">P69905 gene_symbol=HBA1\nMVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHG\n", encoding="utf-8")
    assert ncbi_protein_main(["--gene", "TP53"]) == 2
    assert uniprot_main(["--accession", "P04637"]) == 2
    assert cello_main(["--input", str(fasta_path)]) == 2
    assert cell_ploc_main(["--input", str(fasta_path)]) == 2


def test_rnalocate_task_requires_protocol_check_file() -> None:
    assert rnalocate_main(["--rna", "MALAT1"]) == 2
