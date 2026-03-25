from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.mirdb_org.index.manifest import (  # noqa: E402
    COMMANDS_DOC,
    PAGE_METADATA,
    README_DOC,
    TASKS,
)
from webpages.mirdb_org.index.tasks.mrna_to_mirna import (  # noqa: E402
    TASK_KEY,
    TASK_METADATA,
    build_output_layout,
    build_summary_entry,
    flatten_result_rows,
    load_genes,
    main,
    parse_search_results,
    split_arg_values,
)


HIT_HTML = """
<html>
<body>
<hr> <b>Gene 5290 is predicted to be targeted by 2 miRNAs in miRDB.</a></b> <hr>
<table border="1" id="table1" style="border-collapse: collapse">
<tr bgcolor="#CCFFFF">
  <td align="center" width="52"><font size="2"><b>Target Detail</b></font></td>
  <td align="center" width="57"><font size="2"><b>Target Rank</b></font></td>
  <td align="center" width="65"><b><font size="2">Target Score</font></b></td>
  <td align="center" width="125"><b><font size="2">miRNA Name</font></b></td>
  <td align="center" width="100"><b><font size="2">Gene Symbol</font></b></td>
  <td align="left"><b><font size="2">Gene Description</font></b></td>
</tr>
<tr bgcolor="">
  <td align="center" width="52"><p align="center"><font size="2"><a href="/cgi-bin/target_detail.cgi?targetID=778302">Details</a></font></p></td>
  <td align="center" width="57"><font size="2">1</font></td>
  <td align="left" width="65"><p align="center"><font size="2">100</font></p></td>
  <td align="center" width="125"><font size="2"><a href="/cgi-bin/mature_mir.cgi?name=hsa-miR-548c-3p"> hsa-miR-548c-3p</a></font></td>
  <td align="center" width="100"><font size="2"> PIK3CA</font></td>
  <td align="left"><font size="2">phosphatidylinositol-4,5-bisphosphate 3-kinase catalytic subunit alpha</font></td>
</tr>
<tr bgcolor="#DFDFDF">
  <td align="center" width="52"><p align="center"><font size="2"><a href="/cgi-bin/target_detail.cgi?targetID=2514084">Details</a></font></p></td>
  <td align="center" width="57"><font size="2">2</font></td>
  <td align="left" width="65"><p align="center"><font size="2">98</font></p></td>
  <td align="center" width="125"><font size="2"><a href="/cgi-bin/mature_mir.cgi?name=hsa-miR-186-5p"> hsa-miR-186-5p</a></font></td>
  <td align="center" width="100"><font size="2"> PIK3CA</font></td>
  <td align="left"><font size="2">phosphatidylinositol-4,5-bisphosphate 3-kinase catalytic subunit alpha</font></td>
</tr>
</table>
</body>
</html>
"""

NO_RESULT_HTML = """
<html>
<body>
<h2><font color="#FF0000">Warning: no Human miRNA is predicted to target symbol "NO_SUCH_GENE"</font></h2>
</body>
</html>
"""


def test_manifest_exposes_page_and_task_metadata() -> None:
    task_entry = TASKS[TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://mirdb.org/"
    assert PAGE_METADATA["interaction_mode"] == "html_search"
    assert Path(task_entry["entrypoint_script"]).exists()
    assert Path(PAGE_METADATA["readme"]).exists()
    assert Path(PAGE_METADATA["commands_doc"]).exists()
    assert task_entry["preferred_output_mode"] == "job_dir"
    assert task_entry["master_file_name"] == "mirdb_result.csv"
    assert task_entry["master_file_is_concatenated"] is False
    assert task_entry["protocol_check_required"] is True
    assert "query_mirna_count" in task_entry["master_file_required_columns"]


def test_top_level_docs_reference_mirdb_structure_and_boundaries() -> None:
    agent_brief = (ROOT / "scripts" / "AGENT_BRIEF.md").read_text(encoding="utf-8")
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")

    assert "https://mirdb.org/" in agent_brief
    assert "webpages\\mirdb_org\\index" in task_index
    assert "mRNA biomarker -> miRNA targets (miRDB)" in task_index


def test_page_docs_cover_output_contract_and_scope_boundary() -> None:
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")
    task_entry = TASKS[TASK_KEY]

    assert "当前已代码化任务" in readme
    assert "mRNA biomarker -> mature miRNA" in readme
    assert "不做交集" in readme
    assert "## help" in commands
    assert "## smoke" in commands
    assert "## task" in commands
    assert "## debug" in commands
    assert "## long-running" in commands
    assert "protocol_gate.py" in commands
    assert "--query-count" in commands
    assert task_entry["smoke_command"] in commands


def test_split_arg_values_accepts_comma_separated_inputs() -> None:
    assert split_arg_values(["PIK3CA, ITGB2", "GABBR1"]) == ["PIK3CA", "ITGB2", "GABBR1"]


def test_load_genes_supports_text_csv_and_casefolded_dedup(tmp_path: Path) -> None:
    text_input = tmp_path / "genes.txt"
    text_input.write_text("# comment\nPIK3CA\nitgb2, PIK3CA\n", encoding="utf-8")
    csv_input = tmp_path / "genes.csv"
    csv_input.write_text("gene_symbol\nPIK3CA\nGABBR1\n", encoding="utf-8")

    class Args:
        gene = ["pik3ca", "ITGB2"]
        input = text_input

    assert load_genes(Args()) == ["pik3ca", "ITGB2"]

    class CsvArgs:
        gene = []
        input = csv_input

    assert load_genes(CsvArgs()) == ["PIK3CA", "GABBR1"]


def test_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    class Args:
        job_dir = tmp_path / "mirdb_job"
        job_name = None
        output_prefix = None
        raw_dir = Path("raw")
        input = tmp_path / "input.csv"

    layout = build_output_layout(args=Args(), genes=["PIK3CA"])
    assert layout["mode"] == "job_dir"
    assert layout["job_dir"] == tmp_path / "mirdb_job"
    assert layout["master_csv_path"] == tmp_path / "mirdb_job" / "mirdb_result.csv"
    assert layout["summary_path"] == tmp_path / "mirdb_job" / "temp" / "summary.json"
    assert layout["errors_path"] == tmp_path / "mirdb_job" / "temp" / "errors.json"
    assert layout["raw_dir"] == tmp_path / "mirdb_job" / "temp" / "raw"


def test_parse_search_results_preserves_metadata_and_rows() -> None:
    metadata, rows, error_message = parse_search_results(HIT_HTML)
    flattened = flatten_result_rows("PIK3CA", rows)
    summary = build_summary_entry(metadata, rows)

    assert TASK_METADATA["task_key"] == "mrna_to_mirna"
    assert TASK_METADATA["master_file_mode"] == "direct_generated_master_file"
    assert metadata["gene_id"] == "5290"
    assert metadata["reported_mirna_count"] == 2
    assert error_message is None
    assert len(rows) == 2
    assert rows[0]["target_detail_id"] == "778302"
    assert rows[0]["mirna_name"] == "hsa-miR-548c-3p"
    assert flattened[1]["query_gene_symbol"] == "PIK3CA"
    assert summary["mirna_count"] == 2
    assert summary["mirnas"] == ["hsa-miR-186-5p", "hsa-miR-548c-3p"]


def test_parse_search_results_handles_zero_hit_warning() -> None:
    metadata, rows, error_message = parse_search_results(NO_RESULT_HTML)
    summary = build_summary_entry(metadata, rows)

    assert metadata["reported_mirna_count"] == 0
    assert rows == []
    assert error_message is not None
    assert "NO_SUCH_GENE" in error_message
    assert summary["mirna_count"] == 0


def test_main_requires_protocol_check_file() -> None:
    result = main(["--gene", "PIK3CA"])
    assert result == 2


def test_main_writes_results_and_errors_without_failing_for_unmatched(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "mirdb_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="mirdb_org.index",
        task_key="mrna_to_mirna",
        mirna_count=None,
        query_count=2,
        input_file=None,
        execution_mode="delegated_subagent",
        subagent_name="MiRDBWorker",
        current_boundary="这回合只做 miRDB 单库验证，不做目录外后续分析。",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_fetch(self, gene: str):
        html_text = HIT_HTML if gene == "PIK3CA" else NO_RESULT_HTML
        return f"https://mirdb.org/cgi-bin/search.cgi?searchBox={gene}", html_text

    monkeypatch.setattr(
        "webpages.mirdb_org.index.tasks.mrna_to_mirna.MiRDBSearchClient.fetch_search_html",
        fake_fetch,
    )

    result = main(
        [
            "--gene",
            "PIK3CA",
            "--gene",
            "NO_SUCH_GENE",
            "--job-dir",
            str(job_dir),
            "--protocol-check-file",
            str(ticket_path),
        ]
    )

    assert result == 0
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    errors = json.loads((job_dir / "temp" / "errors.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((job_dir / "mirdb_result.csv").open("r", encoding="utf-8")))

    assert len(rows) == 2
    assert summary["_meta"]["unmatched_query_genes"] == ["NO_SUCH_GENE"]
    assert summary["results"]["PIK3CA"]["mirna_count"] == 2
    assert summary["results"]["NO_SUCH_GENE"]["mirna_count"] == 0
    assert "NO_SUCH_GENE" in errors
