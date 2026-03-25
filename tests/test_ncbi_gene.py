from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.ncbi_nlm_nih_gov.gene.common.fasta_fetch import (  # noqa: E402
    build_fasta_summary_entry,
    load_transcript_queries,
    parse_fasta_response,
    split_arg_values as split_transcript_values,
)
from webpages.ncbi_nlm_nih_gov.gene.common.gene_resolution import (  # noqa: E402
    build_gene_summary_entry,
    flatten_product_report,
    load_genes,
    split_arg_values as split_gene_values,
)
from webpages.ncbi_nlm_nih_gov.gene.manifest import COMMANDS_DOC, PAGE_METADATA, README_DOC, TASKS  # noqa: E402
from webpages.ncbi_nlm_nih_gov.gene.tasks.gene_set_to_fasta_bundle import (  # noqa: E402
    TASK_KEY as BUNDLE_TASK_KEY,
    build_output_layout as build_bundle_output_layout,
    main as gene_set_to_fasta_bundle_main,
)


PRODUCT_REPORT_FIXTURE = {
    "reports": [
        {
            "product": {
                "gene_id": "5290",
                "symbol": "PIK3CA",
                "description": "phosphatidylinositol-4,5-bisphosphate 3-kinase catalytic subunit alpha",
                "tax_id": "9606",
                "taxname": "Homo sapiens",
                "type": "PROTEIN_CODING",
                "transcripts": [
                    {
                        "accession_version": "NM_006218.4",
                        "length": 9259,
                        "cds": {"range": [{"begin": "324", "end": "3530", "orientation": "plus"}]},
                        "genomic_locations": [{"genomic_accession_version": "NC_000003.12", "genomic_range": {"begin": "179148357", "end": "179240093", "orientation": "plus"}, "exons": [{"order": 1}, {"order": 2}]}],
                        "ensembl_transcript": "ENST00000263967.4",
                        "protein": {"accession_version": "NP_006209.2", "name": "isoform 1"},
                        "type": "PROTEIN_CODING",
                        "select_category": "MANE_SELECT",
                    },
                    {
                        "accession_version": "XM_006713658.5",
                        "name": "transcript variant X1",
                        "length": 9106,
                        "cds": {"range": [{"begin": "171", "end": "3377", "orientation": "plus"}]},
                        "genomic_locations": [{"genomic_accession_version": "NC_000003.12", "genomic_range": {"begin": "179148126", "end": "179240093", "orientation": "plus"}, "exons": [{"order": 1}]}],
                        "protein": {"accession_version": "XP_006713721.1", "name": "isoform X1"},
                        "type": "PROTEIN_CODING_MODEL",
                    },
                ],
            },
            "query": ["PIK3CA"],
        }
    ],
    "total_count": 1,
}

FASTA_FIXTURE = """>NM_006218.4 Homo sapiens phosphatidylinositol-4,5-bisphosphate 3-kinase catalytic subunit alpha (PIK3CA), mRNA
AGTTCCGGTGCCGCCGCTGCGGCCGCTGAGGTGTCGGGCTGCTGCTGCCGCGGCCGCTGGGACTGGGGCT
GGGGCCGCCGGCGAGGCAGGGCTCGGGCCCGGCCGGGCAGCTCCGGAGCGGCGGGGGAGAGGGGCCGGGA
"""


def test_manifest_exposes_bundle_metadata() -> None:
    bundle_task = TASKS[BUNDLE_TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://www.ncbi.nlm.nih.gov/"
    assert PAGE_METADATA["interaction_mode"] == "api"
    assert Path(bundle_task["entrypoint_script"]).exists()
    assert bundle_task["protocol_check_required"] is True
    assert "recommended_transcripts.csv" in bundle_task["required_output_files"]
    assert "recommended_transcripts.fasta" in bundle_task["required_output_files"]


def test_top_level_docs_reference_bundle_only_contract() -> None:
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")
    assert "gene set -> recommended-transcript FASTA bundle (NCBI)" in task_index
    assert "gene_set_to_fasta_bundle" in readme
    assert "gene_set_to_fasta_bundle" in commands


def test_common_input_helpers_work(tmp_path: Path) -> None:
    text_input = tmp_path / "genes.txt"
    text_input.write_text("# comment\nPIK3CA\nitgb2, PIK3CA\n", encoding="utf-8")
    assert load_genes(gene_args=["GABBR1"], input_path=text_input) == ["GABBR1", "PIK3CA", "itgb2"]

    csv_input = tmp_path / "transcripts.csv"
    csv_input.write_text(
        "query_gene_symbol,gene_symbol,transcript_accession_version\nPIK3CA,PIK3CA,NM_006218.4\n",
        encoding="utf-8",
    )
    queries = load_transcript_queries(transcript_args=[], input_path=csv_input)
    assert queries[0]["query_gene_symbol"] == "PIK3CA"
    assert queries[0]["query_transcript_accession"] == "NM_006218.4"
    assert split_gene_values(["PIK3CA, ITGB2", "GABBR1"]) == ["PIK3CA", "ITGB2", "GABBR1"]
    assert split_transcript_values(["NM_006218.4, XM_006713658.5"]) == ["NM_006218.4", "XM_006713658.5"]


def test_common_parsers_work() -> None:
    product = PRODUCT_REPORT_FIXTURE["reports"][0]["product"]
    rows = flatten_product_report("PIK3CA", product)
    summary = build_gene_summary_entry(product, rows)
    accession_version, header, sequence = parse_fasta_response(FASTA_FIXTURE)
    fasta_summary = build_fasta_summary_entry(
        {
            "query_gene_symbol": "PIK3CA",
            "gene_symbol": "PIK3CA",
            "transcript_accession_version": accession_version,
            "sequence_length": len(sequence),
            "fasta_header": "NM_006218.4 gene_symbol=PIK3CA query_gene_symbol=PIK3CA source=NCBI",
        }
    )
    assert rows[0]["transcript_accession_version"] == "NM_006218.4"
    assert summary["recommended_transcript_accession_version"] == "NM_006218.4"
    assert header.startswith("NM_006218.4 Homo sapiens")
    assert fasta_summary["gene_symbol"] == "PIK3CA"


def test_bundle_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    args = SimpleNamespace(job_dir=tmp_path / "bundle_job", job_name=None, output_prefix=None, input=tmp_path / "genes.csv", taxon="Homo sapiens")
    layout = build_bundle_output_layout(args=args, genes=["PIK3CA"])
    assert layout["job_dir"] == tmp_path / "bundle_job"
    assert layout["gene_list_path"] == tmp_path / "bundle_job" / "temp" / "query_genes.txt"
    assert layout["fasta_path"] == tmp_path / "bundle_job" / "recommended_transcripts.fasta"


def test_bundle_main_requires_protocol_check_file() -> None:
    assert gene_set_to_fasta_bundle_main(["--gene", "PIK3CA"]) == 2


def test_bundle_main_writes_combined_ncbi_outputs(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "bundle_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="ncbi_nlm_nih_gov.gene",
        task_key="gene_set_to_fasta_bundle",
        mirna_count=None,
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the one-step NCBI bundle path and does not run mRSLPred.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_gene_fetch(self, gene_symbol: str, taxon: str):
        return f"https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/{gene_symbol}/taxon/{taxon}/product_report", PRODUCT_REPORT_FIXTURE

    def fake_fasta_fetch(self, accession: str):
        return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?id={accession}", FASTA_FIXTURE

    monkeypatch.setattr("webpages.ncbi_nlm_nih_gov.gene.tasks.gene_set_to_fasta_bundle.NcbiGeneClient.fetch_product_report", fake_gene_fetch)
    monkeypatch.setattr("webpages.ncbi_nlm_nih_gov.gene.tasks.gene_set_to_fasta_bundle.NcbiFastaClient.fetch_fasta_text", fake_fasta_fetch)

    result = gene_set_to_fasta_bundle_main(
        ["--gene", "PIK3CA", "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)]
    )

    assert result == 0
    assert (job_dir / "recommended_transcripts.csv").exists()
    assert (job_dir / "recommended_transcripts.fasta").exists()
    assert (job_dir / "temp" / "query_genes.txt").exists()
    assert (job_dir / "temp" / "all_transcripts.csv").exists()
    assert (job_dir / "temp" / "recommended_transcript_fasta_records.csv").exists()
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["fasta_row_count"] == 1
    assert summary["gene_symbol_to_transcript"]["PIK3CA"]["recommended_transcript_accession_version"] == "NM_006218.4"
