from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from webpages.diana_e_ce_uth_gr.lncbasev3_home.manifest import (  # noqa: E402
    COMMANDS_DOC,
    PAGE_METADATA,
    README_DOC,
    TASKS,
)
from webpages.diana_e_ce_uth_gr.lncbasev3_home.tasks.mirna_to_lncrna import (  # noqa: E402
    TASK_KEY,
    TASK_METADATA,
    annotate_rows_with_query_count,
    build_output_layout,
    build_summary_entry,
    flatten_result_rows,
    load_mirnas,
    split_arg_values,
)


def test_manifest_exposes_page_and_task_metadata() -> None:
    task_entry = TASKS[TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://diana.e-ce.uth.gr/lncbasev3/home"
    assert PAGE_METADATA["interaction_mode"] == "api"
    assert Path(task_entry["entrypoint_script"]).exists()
    assert Path(PAGE_METADATA["readme"]).exists()
    assert Path(PAGE_METADATA["commands_doc"]).exists()
    assert task_entry["preferred_output_mode"] == "job_dir"
    assert task_entry["master_file_name"] == "lncbasev3_result.csv"
    assert task_entry["master_file_is_concatenated"] is False
    assert task_entry["protocol_check_required"] is True
    assert "query_lncrna_count" in task_entry["master_file_required_columns"]


def test_top_level_docs_reference_structure_and_long_task_rules() -> None:
    start_here = (ROOT / "scripts" / "START_HERE.md").read_text(encoding="utf-8")
    agent_brief = (ROOT / "scripts" / "AGENT_BRIEF.md").read_text(encoding="utf-8")
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")

    assert "AGENT_BRIEF.md" in start_here
    assert "TASK_INDEX.md" in start_here
    assert "webpages\\diana_e_ce_uth_gr\\lncbasev3_home" in task_index
    assert "长任务必须交给子智能体执行" in agent_brief
    assert "本目录下脚本能够完成的部分" in agent_brief
    assert "只交付当前子任务，不补做后续阶段" in start_here
    assert "主线程本回合必须停住" in start_here
    assert "结果汇报格式、输出目录规则、总文件规则都属于网页内约定" in agent_brief
    assert "只有用户明确要求查看结果、查看进度或继续下一阶段时，才允许重新查询子智能体" in agent_brief


def test_page_docs_cover_output_contract() -> None:
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")
    task_entry = TASKS[TASK_KEY]

    assert "当前已代码化任务" in readme
    assert "单任务目录" in readme
    assert "query_lncrna_count" in readme
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
    assert "--job-dir" in commands


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
        job_dir=tmp_path / "lncbasev3_home__mirna_to_lncrna__demo",
        job_name=None,
        output_prefix=None,
        raw_dir=Path("raw"),
        input=tmp_path / "input.csv",
    )
    layout = build_output_layout(args=args, mirnas=["hsa-miR-21-5p"])

    assert layout["mode"] == "job_dir"
    assert layout["job_dir"] == tmp_path / "lncbasev3_home__mirna_to_lncrna__demo"
    assert layout["master_csv_path"] == tmp_path / "lncbasev3_home__mirna_to_lncrna__demo" / "lncbasev3_result.csv"
    assert layout["summary_path"] == tmp_path / "lncbasev3_home__mirna_to_lncrna__demo" / "temp" / "summary.json"
    assert layout["errors_path"] == tmp_path / "lncbasev3_home__mirna_to_lncrna__demo" / "temp" / "errors.json"
    assert layout["raw_dir"] == tmp_path / "lncbasev3_home__mirna_to_lncrna__demo" / "temp" / "raw"


def test_flatten_rows_summary_and_count_column_follow_expected_shape() -> None:
    payload = {
        "noOfInteractions": 3,
        "noOfPublications": 2,
        "noOfCellLines": 1,
        "noOfTissues": 1,
        "methods": ["PAR-CLIP"],
        "results": [
            {
                "interactionId": 12,
                "mirnaName": "hsa-miR-21-5p",
                "geneName": "MALAT1",
                "externalGeneId": "ENSG00000251562",
                "externalTranscriptId": "ENST00000534336",
                "dbName": "LncBase",
                "biotype": "lncRNA",
                "chromosome": "11",
                "confidenceLevel": "high",
                "predictedScore": 0.91,
                "hasSnps": "No",
                "noOfExperiments": 2,
                "noOfPublications": 2,
                "noOfCellLines": 1,
                "noOfTissues": 1,
                "noOfHighThroughput": 1,
                "noOfLowThroughput": 1,
                "expressionCellType": "A549",
                "expressionTissue": "lung",
                "expressionCategory": "matched",
                "mirbaseLink": "mirbase",
                "geneEnsemblLink": "ensembl",
            },
            {
                "interactionId": 12,
                "mirnaName": "hsa-miR-21-5p",
                "geneName": "MALAT1",
            },
            {
                "interactionId": 13,
                "mirnaName": "hsa-miR-21-5p",
                "geneName": "NEAT1",
                "externalTranscriptId": "ENST00000501122",
            },
        ],
    }

    rows = flatten_result_rows("hsa-miR-21-5p", payload)
    summary = build_summary_entry(payload, rows)
    annotate_rows_with_query_count(rows, summary["lncrna_count"])

    assert TASK_METADATA["task_key"] == "mirna_to_lncrna"
    assert TASK_METADATA["master_file_mode"] == "direct_generated_master_file"
    assert len(rows) == 2
    assert [row["gene_name"] for row in rows] == ["MALAT1", "NEAT1"]
    assert all(row["query_lncrna_count"] == 2 for row in rows)
    assert summary["lncrna_count"] == 2
    assert summary["lncrnas"] == ["MALAT1", "NEAT1"]
    assert summary["methods"] == ["PAR-CLIP"]
