from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.rnasysu_com.encori.manifest import (  # noqa: E402
    COMMANDS_DOC,
    PAGE_METADATA,
    README_DOC,
    TASKS,
)
from webpages.rnasysu_com.encori.tasks.mrna_to_mirna import (  # noqa: E402
    TASK_KEY,
    TASK_METADATA,
    annotate_rows_with_query_count,
    build_output_layout,
    build_summary_entry,
    flatten_result_rows,
    load_genes,
    main,
    parse_args,
    parse_response_table,
    split_arg_values,
)


HG38_RESPONSE = """#please cite:
#1.reference
 miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tstart\tend\tstrand\tclipExpNum\tdegraExpNum\tRBP\tmerClass\tmiRseq\talign\ttargetSeq\tTDMDScore\tphyloP\tpancancerNum\tcellline/tissue
MIMAT0000073\thsa-miR-19a-3p\tENSG00000121879\tPIK3CA\tprotein_coding\tchr3\t178916856\t178916878\t+\t7\t0\tAGO2\t8mer\tugugcaaaucuauguugcacu\t||| |||||||||||||||||\tagggguuucgauacaacguga\t0.233\t0.712\t0\tHEK293
MIMAT0004482\thsa-miR-384\tENSG00000121879\tPIK3CA\tprotein_coding\tchr3\t178952085\t178952107\t+\t1\t0\tAGO2\t7mer-m8\tauuuuuggcaggguaaagauga\t|| |||||||||||||| |||\ttgacaaacguccauuuucucu\t0.182\t0.411\t0\tHepG2
"""

NO_RESULT_RESPONSE = """#please cite:
#1.reference
 miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tstart\tend\tstrand\tclipExpNum\tdegraExpNum\tRBP\tmerClass\tmiRseq\talign\ttargetSeq\tTDMDScore\tphyloP\tpancancerNum\tcellline/tissue
No Available results.
"""


def test_manifest_exposes_encori_mrna_task_metadata() -> None:
    task_entry = TASKS[TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://rnasysu.com/encori/"
    assert task_entry["bio_goal"] == "mRNA biomarker -> miRNA targets"
    assert Path(task_entry["entrypoint_script"]).exists()
    assert task_entry["preferred_output_mode"] == "job_dir"
    assert task_entry["master_file_name"] == "encori_result.csv"
    assert task_entry["protocol_check_required"] is True
    assert "query_mirna_count" in task_entry["master_file_required_columns"]


def test_top_level_docs_reference_encori_mrna_task() -> None:
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")

    assert "mRNA biomarker -> miRNA targets (ENCORI)" in task_index
    assert "`mrna_to_mirna`" in readme
    assert 'python "F:\\bio-script\\scripts\\webpages\\rnasysu_com\\encori\\tasks\\mrna_to_mirna.py" --help' in commands


def test_parse_args_default_filters_follow_contract() -> None:
    args = parse_args(["--gene", "PIK3CA"])
    assert args.assembly == "hg38"
    assert args.clip_exp_num == 1
    assert args.degra_exp_num == 0
    assert args.pancancer_num == 0
    assert args.program_num == 1
    assert args.program == "None"


def test_split_arg_values_accepts_comma_separated_inputs() -> None:
    assert split_arg_values(["PIK3CA, ITGB2", "GABBR1"]) == ["PIK3CA", "ITGB2", "GABBR1"]


def test_load_genes_supports_text_and_csv_inputs(tmp_path: Path) -> None:
    text_input = tmp_path / "genes.txt"
    text_input.write_text("# comment\nPIK3CA\nITGB2, PIK3CA\n", encoding="utf-8")
    text_args = SimpleNamespace(gene=["GABBR1"], input=text_input)
    assert load_genes(text_args) == ["GABBR1", "PIK3CA", "ITGB2"]

    csv_input = tmp_path / "genes.csv"
    csv_input.write_text("gene_symbol\nPIK3CA\nITGB2\n", encoding="utf-8")
    csv_args = SimpleNamespace(gene=[], input=csv_input)
    assert load_genes(csv_args) == ["PIK3CA", "ITGB2"]


def test_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    args = SimpleNamespace(
        job_dir=tmp_path / "encori_mrna_job",
        job_name=None,
        output_prefix=None,
        raw_dir=Path("raw"),
        input=tmp_path / "input.csv",
        assembly="hg38",
    )
    layout = build_output_layout(args=args, genes=["PIK3CA"])

    assert layout["mode"] == "job_dir"
    assert layout["job_dir"] == tmp_path / "encori_mrna_job"
    assert layout["master_csv_path"] == tmp_path / "encori_mrna_job" / "encori_result.csv"
    assert layout["summary_path"] == tmp_path / "encori_mrna_job" / "temp" / "summary.json"
    assert layout["errors_path"] == tmp_path / "encori_mrna_job" / "temp" / "errors.json"
    assert layout["raw_dir"] == tmp_path / "encori_mrna_job" / "temp" / "raw"


def test_parse_response_table_preserves_header_and_rows() -> None:
    header, rows, error_message = parse_response_table(HG38_RESPONSE)
    flattened = flatten_result_rows("PIK3CA", header, rows)
    summary = build_summary_entry(header, rows)
    annotate_rows_with_query_count(flattened, summary["mirna_count"])

    assert TASK_METADATA["task_key"] == "mrna_to_mirna"
    assert TASK_METADATA["master_file_mode"] == "direct_generated_master_file"
    assert len(header) == 20
    assert len(rows) == 2
    assert error_message is None
    assert flattened[0]["geneName"] == "PIK3CA"
    assert flattened[1]["miRNAname"] == "hsa-miR-384"
    assert all(row["query_mirna_count"] == 2 for row in flattened)
    assert summary["mirna_count"] == 2
    assert summary["mirnas"] == ["hsa-miR-19a-3p", "hsa-miR-384"]
    assert summary["row_count"] == 2


def test_parse_no_result_response_is_zero_hit_success() -> None:
    header, rows, error_message = parse_response_table(NO_RESULT_RESPONSE)
    summary = build_summary_entry(header, rows)

    assert len(header) == 20
    assert rows == []
    assert error_message is None
    assert summary["mirna_count"] == 0
    assert summary["row_count"] == 0
    assert summary["mirnas"] == []


def test_main_requires_protocol_check_file() -> None:
    result = main(["--gene", "PIK3CA"])
    assert result == 2


def test_main_writes_results_without_failing_for_zero_hit_gene(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "encori_mrna_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="rnasysu_com.encori",
        task_key="mrna_to_mirna",
        mirna_count=None,
        query_count=2,
        input_file=None,
        execution_mode="delegated_subagent",
        subagent_name="EncoriWorker",
        current_boundary="这回合只做 ENCORI 单库验证，不做交集和高特异性筛选。",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_fetch(
        self,
        gene: str,
        *,
        assembly: str,
        clip_exp_num: int,
        degra_exp_num: int,
        pancancer_num: int,
        program_num: int,
        program: str,
    ):
        payload_text = HG38_RESPONSE if gene == "PIK3CA" else NO_RESULT_RESPONSE
        return f"https://rnasysu.com/encori/moduleDownload.php?gene={gene}", payload_text

    monkeypatch.setattr(
        "webpages.rnasysu_com.encori.tasks.mrna_to_mirna.EncoriMrnaClient.fetch_response_text",
        fake_fetch,
    )

    result = main(
        [
            "--gene",
            "PIK3CA",
            "--gene",
            "GABBR1",
            "--job-dir",
            str(job_dir),
            "--protocol-check-file",
            str(ticket_path),
        ]
    )

    assert result == 0
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((job_dir / "encori_result.csv").open("r", encoding="utf-8")))

    assert len(rows) == 2
    assert summary["results"]["PIK3CA"]["mirna_count"] == 2
    assert summary["results"]["GABBR1"]["mirna_count"] == 0
    assert not (job_dir / "temp" / "errors.json").exists()
