from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from webpages.rnasysu_com.encori.manifest import (  # noqa: E402
    COMMANDS_DOC,
    PAGE_METADATA,
    README_DOC,
    TASKS,
)
from webpages.rnasysu_com.encori.tasks.mirna_to_lncrna import (  # noqa: E402
    TASK_KEY,
    TASK_METADATA,
    annotate_rows_with_query_count,
    build_output_layout,
    build_summary_entry,
    flatten_result_rows,
    load_mirnas,
    parse_args,
    parse_response_table,
    split_arg_values,
)


HG38_RESPONSE = """#please cite:
#1.reference
#2.reference
miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tstart\tend\tstrand\tclipExpNum\tdegraExpNum\tRBP\tmerClass\tmiRseq\talign\ttargetSeq\tTDMDScore\tphyloP\tpancancerNum\tcellline/tissue
MIMAT0000076\thsa-miR-21-5p\tENSG00000255717\tSNHG1\tlncRNA\tchr11\t62854599\t62854622\t-\t32\t0\tAGO1-4,AGO2\t7mer-m8\taguuGUAGUCAG-AC-UAUUCGAu\t::|:: |: || |||||||\tcaguUGUUGUUUAUGAAUAAGCUu\t0.8414\t-0.277\t5\tHuh-7.5
MIMAT0000076\thsa-miR-21-5p\tENSG00000229807\tXIST\tlncRNA\tchrX\t73824092\t73824112\t-\t3\t0\tAGO1-4,AGO2\t8mer\taguuGUAGUCAGACUAUUCGAu\t|| |  | | |||||||\tcugcCACCCAUAU-AUAAGCUa\t0.6031\t0.396\t7\tHEK293S
"""

MM10_RESPONSE = """#please cite:
#1.reference
miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tstart\tend\tstrand\tclipExpNum\tdegraExpNum\tRBP\tmerClass\tmiRseq\talign\ttargetSeq\tTDMDScore\tphyloP\tcellline/tissue
MIMAT0000123\tmmu-miR-1a-3p\tENSMUSG00000090025\tMalat1\tlncRNA\tchr19\t5821823\t5821845\t+\t2\t0\tAgo2\t8mer\tuggaauguaaagaaguauguau\t|| ||||||||||||||||||\tacuaaacaaUUCUUCAUACAUA\t0.702\t0.515\tNIH3T3
"""

INVALID_RESPONSE = """#please cite:
#1.reference
#2.reference
miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tstart\tend\tstrand\tclipExpNum\tdegraExpNum\tRBP\tmerClass\tmiRseq\talign\ttargetSeq\tTDMDScore\tphyloP\tpancancerNum\tcellline/tissue
The "miRNA" parameter haven't been set correctly! Or the input of "miRNA" parameter is not available!
"""

HEADER_ONLY_RESPONSE = """#please cite:
#1.reference
miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tstart\tend\tstrand\tclipExpNum\tdegraExpNum\tRBP\tmerClass\tmiRseq\talign\ttargetSeq\tTDMDScore\tphyloP\tpancancerNum\tcellline/tissue
"""


def test_manifest_exposes_page_and_task_metadata() -> None:
    task_entry = TASKS[TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://rnasysu.com/encori/"
    assert PAGE_METADATA["interaction_mode"] == "api"
    assert Path(task_entry["entrypoint_script"]).exists()
    assert Path(PAGE_METADATA["readme"]).exists()
    assert Path(PAGE_METADATA["commands_doc"]).exists()
    assert task_entry["preferred_output_mode"] == "job_dir"
    assert task_entry["master_file_name"] == "encori_result.csv"
    assert task_entry["master_file_is_concatenated"] is False
    assert task_entry["protocol_check_required"] is True
    assert "query_lncrna_count" in task_entry["master_file_required_columns"]


def test_top_level_docs_reference_encori_structure_and_boundaries() -> None:
    start_here = (ROOT / "scripts" / "START_HERE.md").read_text(encoding="utf-8")
    agent_brief = (ROOT / "scripts" / "AGENT_BRIEF.md").read_text(encoding="utf-8")
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")

    assert "https://rnasysu.com/encori/" in agent_brief
    assert "webpages\\rnasysu_com\\encori" in task_index
    assert "本目录只负责 ENCORI 单库 miRNA -> lncRNA 查询" in task_index
    assert "只交付当前子任务，不补做后续阶段" in start_here
    assert "主线程本回合必须停住" in start_here
    assert "本目录下脚本能够完成的部分" in agent_brief
    assert "长任务下派后，主线程不要同步等待到底，不要轮询状态，不要检查输出" in agent_brief


def test_page_docs_cover_output_contract_and_scope_boundary() -> None:
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")
    task_entry = TASKS[TASK_KEY]

    assert "当前已代码化任务" in readme
    assert "单任务目录" in readme
    assert "不调用 LncBase" in readme
    assert "不做交集" in readme
    assert "## help" in commands
    assert "## smoke" in commands
    assert "## task" in commands
    assert "## debug" in commands
    assert "## long-running" in commands
    assert "## 输出约定" in commands
    assert "protocol_gate.py" in commands
    assert "--protocol-check-file" in commands
    assert task_entry["smoke_command"] in commands
    assert task_entry["help_command"] in commands
    assert "--timeout" not in task_entry["smoke_command"]


def test_parse_args_default_filters_follow_contract() -> None:
    args = parse_args(["--mirna", "hsa-miR-21-5p"])
    assert args.assembly == "hg38"
    assert args.clip_exp_num == 1
    assert args.degra_exp_num == 0
    assert args.pancancer_num == 0
    assert args.program_num == 1
    assert args.program == "None"
    assert args.target == "all"
    assert args.cell_type == "all"


def test_split_arg_values_accepts_comma_separated_inputs() -> None:
    assert split_arg_values(["hsa-miR-21-5p, hsa-miR-1", "hsa-miR-155-5p"]) == [
        "hsa-miR-21-5p",
        "hsa-miR-1",
        "hsa-miR-155-5p",
    ]


def test_load_mirnas_supports_text_and_csv_inputs(tmp_path: Path) -> None:
    text_input = tmp_path / "mirnas.txt"
    text_input.write_text("# comment\nhsa-miR-1\nhsa-miR-21-5p, hsa-miR-1\n", encoding="utf-8")
    text_args = SimpleNamespace(mirna=["hsa-miR-21-5p", "hsa-miR-155-5p"], input=text_input)
    assert load_mirnas(text_args) == ["hsa-miR-21-5p", "hsa-miR-155-5p", "hsa-miR-1"]

    csv_input = tmp_path / "mirnas.csv"
    csv_input.write_text("miRNA\nhsa-miR-128-3p\nhsa-miR-132-3p\n", encoding="utf-8")
    csv_args = SimpleNamespace(mirna=[], input=csv_input)
    assert load_mirnas(csv_args) == ["hsa-miR-128-3p", "hsa-miR-132-3p"]


def test_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    args = SimpleNamespace(
        job_dir=tmp_path / "encori__mirna_to_lncrna__hg38__demo",
        job_name=None,
        output_prefix=None,
        raw_dir=Path("raw"),
        input=tmp_path / "input.csv",
        assembly="hg38",
    )
    layout = build_output_layout(args=args, mirnas=["hsa-miR-21-5p"])

    assert layout["mode"] == "job_dir"
    assert layout["job_dir"] == tmp_path / "encori__mirna_to_lncrna__hg38__demo"
    assert layout["master_csv_path"] == tmp_path / "encori__mirna_to_lncrna__hg38__demo" / "encori_result.csv"
    assert layout["summary_path"] == tmp_path / "encori__mirna_to_lncrna__hg38__demo" / "temp" / "summary.json"
    assert layout["errors_path"] == tmp_path / "encori__mirna_to_lncrna__hg38__demo" / "temp" / "errors.json"
    assert layout["raw_dir"] == tmp_path / "encori__mirna_to_lncrna__hg38__demo" / "temp" / "raw"


def test_parse_hg38_response_preserves_original_header_and_rows() -> None:
    header, rows, error_message = parse_response_table(HG38_RESPONSE)
    flattened = flatten_result_rows("hsa-miR-21-5p", header, rows)
    summary = build_summary_entry(header, rows)
    annotate_rows_with_query_count(flattened, summary["lncrna_count"])

    assert TASK_METADATA["task_key"] == "mirna_to_lncrna"
    assert TASK_METADATA["master_file_mode"] == "direct_generated_master_file"
    assert len(header) == 20
    assert len(rows) == 2
    assert error_message is None
    assert flattened[0]["geneName"] == "SNHG1"
    assert flattened[1]["geneName"] == "XIST"
    assert all(row["query_lncrna_count"] == 2 for row in flattened)
    assert summary["lncrna_count"] == 2
    assert summary["lncrnas"] == ["SNHG1", "XIST"]
    assert summary["row_count"] == 2
    assert summary["response_header"] == header


def test_parse_mm10_response_handles_missing_pancancer_column() -> None:
    header, rows, error_message = parse_response_table(MM10_RESPONSE)

    assert len(header) == 19
    assert "pancancerNum" not in header
    assert len(rows) == 1
    assert rows[0]["geneName"] == "Malat1"
    assert error_message is None


def test_parse_invalid_mirna_response_returns_error_message() -> None:
    header, rows, error_message = parse_response_table(INVALID_RESPONSE)

    assert len(header) == 20
    assert rows == []
    assert error_message is not None
    assert 'The "miRNA" parameter' in error_message


def test_parse_header_only_response_is_zero_hit_success() -> None:
    header, rows, error_message = parse_response_table(HEADER_ONLY_RESPONSE)
    summary = build_summary_entry(header, rows)

    assert len(header) == 20
    assert rows == []
    assert error_message is None
    assert summary["lncrna_count"] == 0
    assert summary["row_count"] == 0
    assert summary["lncrnas"] == []
