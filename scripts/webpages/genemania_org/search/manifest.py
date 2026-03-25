"""Machine-readable metadata for the GeneMANIA search webpage package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
TASK_SCRIPT = PAGE_DIR / "tasks" / "gene_set_to_report_figure.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "GeneSetAnalysis_GeneMANIA_default"
SMOKE_JOB_DIR = ROOT / "outputs" / "tasks" / "GeneSetAnalysis_GeneMANIA_smoke_GABBR1_PIK3CA_ITGB2"

PAGE_METADATA = {
    "page_key": "genemania_org.search",
    "homepage": "https://genemania.org/",
    "page_type": "webpage",
    "interaction_mode": "browser_automation",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "gene_set_to_report_figure": {
        "task_key": "gene_set_to_report_figure",
        "bio_category": "Gene set",
        "bio_goal": "Gene set -> GeneMANIA report figure",
        "description": "Open a GeneMANIA result page, apply top-function coloring and export a cleaned PDF + PNG.",
        "entrypoint_script": str(TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(DEFAULT_JOB_DIR),
        "master_file_name": "genemania_report.pdf",
        "master_file_mode": "single_report_pdf",
        "master_file_is_concatenated": False,
        "master_file_required_columns": [],
        "required_output_files": ["genemania_report.pdf", "genemania_report.png"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": False,
        "test_output_cleanup_required": True,
        "test_output_cleanup_scope": (
            "Delete smoke/test job directories after verification unless the user explicitly asks to keep them."
        ),
        "help_command": f'python "{TASK_SCRIPT}" --help',
        "smoke_command": (
            f'python "{TASK_SCRIPT}" --gene GABBR1 --gene PIK3CA --gene ITGB2 '
            f'--job-dir "{SMOKE_JOB_DIR}"'
        ),
        "task_command_template": (
            f'python "{TASK_SCRIPT}" --gene GABBR1 --gene PIK3CA --gene ITGB2 '
            f'--job-dir "{DEFAULT_JOB_DIR}"'
        ),
        "long_running": False,
        "result_reporting_template": [
            "script used",
            "query genes",
            "job directory",
            "report pdf path",
            "report png path",
            "errors file presence",
            "selected function count",
            "final url",
        ],
    }
}

DELEGATION_NOTES = {
    "background": (
        "This page is driven by GeneMANIA webpage automation only. "
        "The implemented task exports a cleaned first-page report PDF and a matching PNG preview."
    ),
    "long_task_policy": {
        "delegate_to_subagent": False,
        "batch_input_requires_subagent": False,
        "main_thread_waits_to_completion": True,
        "main_thread_default_reply": [
            "executed locally",
            "command",
            "output path",
        ],
        "query_results_later": False,
        "stop_on_user_request": False,
    },
    "workflow": [
        "Read README.md, COMMANDS.md, and manifest.py before executing.",
        "Run the help command or smoke command first.",
        "Only after a successful smoke run should you attempt a larger formal task.",
        "Delete smoke/test outputs after verification unless the user explicitly asks to keep them.",
        "Install pypdfium2 before a formal PNG export if it is not already available.",
    ],
    "must_include": [
        "background information",
        "task goal",
        "recommended command",
        "smoke/test command",
        "optional PNG renderer dependency",
    ],
    "do_not": [
        "Do not migrate the Java CLI batch runner into this webpage package.",
        "Do not migrate the R report helper into this webpage package.",
        "Do not output webpage toolbars or raw network PNGs as the formal deliverable.",
        "Do not silently fall back to half-complete output when PDF-to-PNG rendering dependencies are missing.",
    ],
}
