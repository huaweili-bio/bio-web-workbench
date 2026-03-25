from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.rnalocate_org.search.common.core import build_search_url, parse_search_results  # noqa: E402
from webpages.rnalocate_org.search.common.core import RNALocateError  # noqa: E402
from webpages.rnalocate_org.search.manifest import TASKS as RNALOCATE_TASKS  # noqa: E402
from webpages.rnalocate_org.search.tasks.rna_symbol_to_localization_annotation import main as rnalocate_main  # noqa: E402


RNALOCATE_HTML = """
<html><body>
<table>
  <tr>
    <th>Symbol</th>
    <th>RNA Category</th>
    <th>Species</th>
    <th>Localization</th>
    <th>Sources</th>
    <th>PMID</th>
    <th>Score</th>
  </tr>
  <tr>
    <td>MALAT1</td>
    <td>lncRNA</td>
    <td>Homo sapiens</td>
    <td>Nucleus</td>
    <td>Experiment validation</td>
    <td>12345678</td>
    <td>0.95</td>
  </tr>
</table>
</body></html>
"""


def test_task_index_mentions_rnalocate() -> None:
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")
    assert "RNA symbol -> localization annotation (RNALocate)" in task_index


def test_manifest_exposes_rnalocate_task_metadata() -> None:
    assert "rna_symbol_to_localization_annotation" in RNALOCATE_TASKS


def test_build_search_url_contains_expected_parameters() -> None:
    url = build_search_url(keyword="MALAT1", dataset="Symbol", category="lncRNA", species="Homo sapiens", sources="Experiment validation")
    assert "Keyword=MALAT1" in url
    assert "dataset=Symbol" in url
    assert "category=lncRNA" in url
    assert "searchType=home" in url


def test_parse_search_results_extracts_table_rows() -> None:
    rows = parse_search_results(query_keyword="MALAT1", payload=RNALOCATE_HTML)
    assert rows[0]["rna_symbol"] == "MALAT1"
    assert rows[0]["localization"] == "Nucleus"
    assert rows[0]["category"] == "lncRNA"


def test_rnalocate_task_writes_result_table(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "rnalocate_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="rnalocate_org.search",
        task_key="rna_symbol_to_localization_annotation",
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the one-step RNALocate annotation path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(
        "webpages.rnalocate_org.search.tasks.rna_symbol_to_localization_annotation.fetch_search_html",
        lambda **_: RNALOCATE_HTML,
    )
    result = rnalocate_main(["--rna", "MALAT1", "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 0
    assert (job_dir / "rnalocate_localization_annotation.tsv").exists()
    assert "Nucleus" in (job_dir / "rnalocate_localization_annotation.tsv").read_text(encoding="utf-8")


def test_rnalocate_task_returns_error_when_all_queries_fail(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "rnalocate_job_failed"
    ticket_path = tmp_path / "protocol_check_failed.json"
    payload = create_protocol_ticket(
        page_key="rnalocate_org.search",
        task_key="rna_symbol_to_localization_annotation",
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="This turn only validates the failed RNALocate annotation path.",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _raise_error(**_: object) -> str:
        raise RNALocateError("HTTP 500")

    monkeypatch.setattr(
        "webpages.rnalocate_org.search.tasks.rna_symbol_to_localization_annotation.fetch_search_html",
        _raise_error,
    )
    result = rnalocate_main(["--rna", "MALAT1", "--job-dir", str(job_dir), "--protocol-check-file", str(ticket_path)])
    assert result == 1
    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["result_status"] == "failed"
    assert (job_dir / "temp" / "errors.json").exists()
