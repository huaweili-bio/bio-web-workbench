"""Machine-readable metadata for the CELLO package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
TASK_SCRIPT = PAGE_DIR / "tasks" / "protein_fasta_to_localization.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "ProteinLoc_CELLO_default"

PAGE_METADATA = {
    "page_key": "cello_life_nctu_edu_tw.root",
    "homepage": "https://cello.life.nctu.edu.tw/",
    "page_type": "webpage",
    "interaction_mode": "web_form",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "protein_fasta_to_localization": {
        "task_key": "protein_fasta_to_localization",
        "bio_category": "protein",
        "bio_goal": "protein FASTA -> localization prediction",
        "description": "Submit protein FASTA queries to CELLO and parse localization predictions from the returned HTML. Supports coding nucleotide input via --seqtype dna.",
        "entrypoint_script": str(TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(DEFAULT_JOB_DIR),
        "master_file_name": "protein_localization_result.csv",
        "master_file_mode": "single_table",
        "master_file_is_concatenated": False,
        "master_file_required_columns": ["sequence_id", "predicted_locations", "source_method"],
        "required_output_files": ["protein_localization_result.csv"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "help_command": f'python "{TASK_SCRIPT}" --help',
        "task_command_template": f'python "{TASK_SCRIPT}" --input "F:\\bio-script\\data\\protein_smoke.fasta" --job-dir "{DEFAULT_JOB_DIR}"',
        "long_running": False,
    },
}
