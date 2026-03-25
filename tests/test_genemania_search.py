from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from protocol_gate import create_protocol_ticket  # noqa: E402
from webpages.genemania_org.search.manifest import (  # noqa: E402
    COMMANDS_DOC,
    PAGE_METADATA,
    README_DOC,
    TASKS,
)
from webpages.genemania_org.search.tasks.gene_set_to_report_figure import (  # noqa: E402
    DEFAULT_FOOTER_CROP_RATIO,
    DEFAULT_HEADER_CROP_RATIO,
    TASK_KEY,
    build_output_layout,
    build_query_url,
    crop_pdf_first_page,
    load_genes,
    main,
    render_pdf_to_png,
    split_arg_values,
)


def make_sample_pdf(path: Path, *, pages: int = 2) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_manifest_exposes_page_and_task_metadata() -> None:
    task_entry = TASKS[TASK_KEY]
    assert PAGE_METADATA["homepage"] == "https://genemania.org/"
    assert PAGE_METADATA["interaction_mode"] == "browser_automation"
    assert Path(task_entry["entrypoint_script"]).exists()
    assert Path(PAGE_METADATA["readme"]).exists()
    assert Path(PAGE_METADATA["commands_doc"]).exists()
    assert task_entry["preferred_output_mode"] == "job_dir"
    assert task_entry["master_file_name"] == "genemania_report.pdf"
    assert task_entry["protocol_check_required"] is True
    assert "genemania_report.png" in task_entry["required_output_files"]


def test_top_level_docs_reference_genemania_structure_and_boundaries() -> None:
    agent_brief = (ROOT / "scripts" / "AGENT_BRIEF.md").read_text(encoding="utf-8")
    task_index = (ROOT / "scripts" / "TASK_INDEX.md").read_text(encoding="utf-8")

    assert "https://genemania.org/" in agent_brief
    assert "webpages\\genemania_org\\search" in task_index
    assert "不迁入 Java CLI 批跑" in task_index


def test_page_docs_cover_output_contract_and_single_query_boundary() -> None:
    readme = README_DOC.read_text(encoding="utf-8")
    commands = COMMANDS_DOC.read_text(encoding="utf-8")

    assert "单个基因集 -> 清理后 PDF/PNG 成品图" in readme
    assert "不是网页全页截图" in readme
    assert "不实现 TSV/CSV 多 query 批处理" in readme
    assert "## help" in commands
    assert "## smoke" in commands
    assert "## task" in commands
    assert "## debug" in commands
    assert "## long-running" in commands
    assert "pypdfium2" in commands
    assert "--query-count 1" in commands


def test_split_arg_values_accepts_comma_and_whitespace_inputs() -> None:
    assert split_arg_values(["GABBR1, PIK3CA", "ITGB2 EGFR"]) == ["GABBR1", "PIK3CA", "ITGB2", "EGFR"]


def test_load_genes_casefolds_and_deduplicates() -> None:
    class Args:
        gene = ["gabbr1", "PIK3CA, ITGB2", "GABBR1"]

    assert load_genes(Args()) == ["gabbr1", "PIK3CA", "ITGB2"]


def test_build_query_url_uses_deep_link_format() -> None:
    assert build_query_url("9606", ["GABBR1", "PIK3CA", "ITGB2"]) == (
        "https://genemania.org/link?o=9606&g=GABBR1%7CPIK3CA%7CITGB2"
    )


def test_output_layout_prefers_single_job_directory(tmp_path: Path) -> None:
    class Args:
        job_dir = tmp_path / "genemania_job"
        job_name = None
        output_prefix = None

    layout = build_output_layout(args=Args(), genes=["GABBR1", "PIK3CA", "ITGB2"])
    assert layout["mode"] == "job_dir"
    assert layout["job_dir"] == tmp_path / "genemania_job"
    assert layout["report_pdf_path"] == tmp_path / "genemania_job" / "genemania_report.pdf"
    assert layout["report_png_path"] == tmp_path / "genemania_job" / "genemania_report.png"
    assert layout["summary_path"] == tmp_path / "genemania_job" / "temp" / "summary.json"
    assert layout["errors_path"] == tmp_path / "genemania_job" / "temp" / "errors.json"


def test_crop_pdf_keeps_first_page_and_reduces_page_height(tmp_path: Path) -> None:
    source_pdf = make_sample_pdf(tmp_path / "source.pdf", pages=2)
    output_pdf = tmp_path / "cropped.pdf"

    crop_info = crop_pdf_first_page(source_pdf, output_pdf)

    assert crop_info["header_crop_ratio"] == DEFAULT_HEADER_CROP_RATIO
    assert crop_info["footer_crop_ratio"] == DEFAULT_FOOTER_CROP_RATIO
    assert crop_info["cropped_height_pt"] < crop_info["original_height_pt"]

    from pypdf import PdfReader

    reader = PdfReader(str(output_pdf))
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.height) == crop_info["cropped_height_pt"]


def test_main_requires_protocol_check_file() -> None:
    result = main(["--gene", "GABBR1", "--gene", "PIK3CA", "--gene", "ITGB2"])
    assert result == 2


def test_main_writes_pdf_png_summary_and_deletes_raw_artifacts(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "genemania_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="genemania_org.search",
        task_key="gene_set_to_report_figure",
        mirna_count=None,
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="这回合只做 GeneMANIA 单组基因集导出，不做批量任务，不迁 Java 或 R 流程。",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_collect_web_report(**kwargs):
        make_sample_pdf(kwargs["raw_pdf_path"], pages=3)
        if kwargs["network_png_path"] is not None:
            kwargs["network_png_path"].write_bytes(b"network")
        return {
            "title": "GABBR1 PIK3CA ITGB2 : H. sapiens : GeneMANIA",
            "finalUrl": "https://genemania.org/search/homo-sapiens/GABBR1/PIK3CA/ITGB2",
            "nodeCount": 23,
            "edgeCount": 401,
            "selectedFunctions": [
                {"description": "protein complex involved in cell adhesion", "qValue": 1e-6, "color": "#c26661", "coverage": "5 / 24"},
                {"description": "plasma membrane signaling receptor complex", "qValue": 4e-6, "color": "#639bc7", "coverage": "7 / 161"},
            ],
            "networkGroups": [{"name": "Physical Interactions", "color": "#eaa2a2"}],
        }

    def fake_render_pdf_to_png(input_pdf: Path, output_png: Path, *, dpi: int):
        output_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return {"dpi": dpi, "renderer": "fake", "scale": 1.0, "width_px": 1800, "height_px": 2200}

    monkeypatch.setattr(
        "webpages.genemania_org.search.tasks.gene_set_to_report_figure.collect_web_report",
        fake_collect_web_report,
    )
    monkeypatch.setattr(
        "webpages.genemania_org.search.tasks.gene_set_to_report_figure.render_pdf_to_png",
        fake_render_pdf_to_png,
    )

    result = main(
        [
            "--gene",
            "GABBR1",
            "--gene",
            "PIK3CA",
            "--gene",
            "ITGB2",
            "--job-dir",
            str(job_dir),
            "--protocol-check-file",
            str(ticket_path),
        ]
    )

    assert result == 0
    assert (job_dir / "genemania_report.pdf").exists()
    assert (job_dir / "genemania_report.png").exists()
    assert (job_dir / "temp" / "summary.json").exists()
    assert not (job_dir / "temp" / "errors.json").exists()
    assert not (job_dir / "temp" / "raw_report.pdf").exists()
    assert not (job_dir / "temp" / "network_debug.png").exists()

    summary = json.loads((job_dir / "temp" / "summary.json").read_text(encoding="utf-8"))
    assert summary["_meta"]["query_count"] == 1
    assert summary["_meta"]["report_pdf_path"].endswith("genemania_report.pdf")
    assert summary["result"]["selected_function_count"] == 2
    assert summary["result"]["final_url"].endswith("/GABBR1/PIK3CA/ITGB2")


def test_main_writes_errors_json_when_png_renderer_is_missing(tmp_path: Path, monkeypatch) -> None:
    job_dir = tmp_path / "genemania_job"
    ticket_path = tmp_path / "protocol_check.json"
    payload = create_protocol_ticket(
        page_key="genemania_org.search",
        task_key="gene_set_to_report_figure",
        mirna_count=None,
        query_count=1,
        input_file=None,
        execution_mode="main_thread",
        subagent_name="",
        current_boundary="这回合只做 GeneMANIA 单组基因集导出，不做批量任务，不迁 Java 或 R 流程。",
        job_dir=job_dir,
    )
    ticket_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_collect_web_report(**kwargs):
        make_sample_pdf(kwargs["raw_pdf_path"], pages=2)
        return {
            "title": "demo",
            "finalUrl": "https://genemania.org/search/homo-sapiens/GABBR1/PIK3CA/ITGB2",
            "nodeCount": 1,
            "edgeCount": 1,
            "selectedFunctions": [],
            "networkGroups": [],
        }

    monkeypatch.setattr(
        "webpages.genemania_org.search.tasks.gene_set_to_report_figure.collect_web_report",
        fake_collect_web_report,
    )
    monkeypatch.setattr(
        "webpages.genemania_org.search.tasks.gene_set_to_report_figure.load_pdf_renderer",
        lambda: (_ for _ in ()).throw(
            __import__("webpages.genemania_org.search.tasks.gene_set_to_report_figure", fromlist=["GeneMANIAError"]).GeneMANIAError(
                "Generating report.png requires the optional dependency 'pypdfium2'. Install it with: python -m pip install pypdfium2"
            )
        ),
    )

    result = main(
        [
            "--gene",
            "GABBR1",
            "--gene",
            "PIK3CA",
            "--gene",
            "ITGB2",
            "--job-dir",
            str(job_dir),
            "--protocol-check-file",
            str(ticket_path),
        ]
    )

    assert result == 1
    errors = json.loads((job_dir / "temp" / "errors.json").read_text(encoding="utf-8"))
    assert "pypdfium2" in errors["error"]
    assert (job_dir / "temp" / "raw_report.pdf").exists()


def test_render_pdf_to_png_reports_missing_renderer(monkeypatch, tmp_path: Path) -> None:
    input_pdf = make_sample_pdf(tmp_path / "source.pdf", pages=1)
    output_png = tmp_path / "preview.png"
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "pypdfium2":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    try:
        render_pdf_to_png(input_pdf, output_png, dpi=300)
    except Exception as exc:
        assert "pypdfium2" in str(exc)
    else:
        raise AssertionError("Expected missing renderer error.")
