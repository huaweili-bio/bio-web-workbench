"""Machine-readable metadata for the RNALocate package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
TASK_SCRIPT = PAGE_DIR / "tasks" / "rna_symbol_to_localization_annotation.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "RNALoc_RNALocate_default"

PAGE_METADATA = {
    "page_key": "rnalocate_org.search",
    "homepage": "https://www.rnalocate.org/",
    "page_type": "webpage",
    "interaction_mode": "web_search",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "rna_symbol_to_localization_annotation": {
        "task_key": "rna_symbol_to_localization_annotation",
        "bio_category": "RNA",
        "bio_goal": "RNA symbol -> localization annotation",
        "description": "Query the RNALocate show_search endpoint with exact RNA symbols and parse localization annotations from the returned result table.",
        "entrypoint_script": str(TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(DEFAULT_JOB_DIR),
        "master_file_name": "rnalocate_localization_annotation.tsv",
        "master_file_mode": "single_table",
        "master_file_is_concatenated": False,
        "master_file_required_columns": ["query_rna_symbol", "rna_symbol", "localization"],
        "required_output_files": ["rnalocate_localization_annotation.tsv"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "help_command": f'python "{TASK_SCRIPT}" --help',
        "task_command_template": f'python "{TASK_SCRIPT}" --rna MALAT1 --job-dir "{DEFAULT_JOB_DIR}"',
        "long_running": False,
    },
}
