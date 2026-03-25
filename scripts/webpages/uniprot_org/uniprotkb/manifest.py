"""Machine-readable metadata for the UniProtKB package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
TASK_SCRIPT = PAGE_DIR / "tasks" / "protein_accession_to_localization_annotation.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "ProteinLoc_UniProtKB_default"

PAGE_METADATA = {
    "page_key": "uniprot_org.uniprotkb",
    "homepage": "https://www.uniprot.org/uniprotkb",
    "page_type": "webpage",
    "interaction_mode": "api",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "protein_accession_to_localization_annotation": {
        "task_key": "protein_accession_to_localization_annotation",
        "bio_category": "protein",
        "bio_goal": "protein accession -> localization annotation",
        "description": "Fetch UniProtKB subcellular localization annotations for one or more protein accessions.",
        "entrypoint_script": str(TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(DEFAULT_JOB_DIR),
        "master_file_name": "uniprot_subcellular_annotation.tsv",
        "master_file_mode": "single_table",
        "master_file_is_concatenated": False,
        "master_file_required_columns": ["query_accession", "entry", "subcellular_location_text"],
        "required_output_files": ["uniprot_subcellular_annotation.tsv"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "help_command": f'python "{TASK_SCRIPT}" --help',
        "task_command_template": f'python "{TASK_SCRIPT}" --accession P04637 --job-dir "{DEFAULT_JOB_DIR}"',
        "long_running": False,
    },
}
