"""Machine-readable metadata for the mRSLPred GitHub package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
BUNDLE_TASK_SCRIPT = PAGE_DIR / "tasks" / "fasta_to_localization_bundle.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
BUNDLE_DEFAULT_JOB_DIR = (
    ROOT / "outputs" / "tasks" / "RNALoc_mRSLPred_default"
)
BUNDLE_SMOKE_JOB_DIR = (
    ROOT / "outputs" / "tasks" / "RNALoc_mRSLPred_smoke"
)

PAGE_METADATA = {
    "page_key": "github_com.raghavagps_mrslpred",
    "homepage": "https://github.com/raghavagps/mrslpred",
    "page_type": "webpage",
    "interaction_mode": "local_runtime",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "fasta_to_localization_bundle": {
        "task_key": "fasta_to_localization_bundle",
        "bio_category": "mRNA",
        "bio_goal": "FASTA -> prediction result + PNG/PDF figure",
        "description": "Run the official GitHub mRSLPred standalone script and render mrslpred_localization_figure.png/mrslpred_localization_figure.pdf in the same job directory.",
        "entrypoint_script": str(BUNDLE_TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(BUNDLE_DEFAULT_JOB_DIR),
        "master_file_name": "mrslpred_result.csv",
        "master_file_mode": "multi_file_bundle",
        "master_file_is_concatenated": False,
        "master_file_required_columns": [
            "sequence_id",
            "transcript_accession_version",
            "gene_symbol",
            "predicted_locations",
        ],
        "required_output_files": ["mrslpred_result.csv", "mrslpred_localization_figure.png", "mrslpred_localization_figure.pdf"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "test_output_cleanup_scope": (
            "Delete smoke/test job directories after verification unless the user explicitly asks to keep them."
        ),
        "help_command": f'python "{BUNDLE_TASK_SCRIPT}" --help',
        "smoke_command": (
            f'python "{BUNDLE_TASK_SCRIPT}" --input "F:\\bio-script\\data\\mrslpred_smoke.fasta" '
            f'--job-dir "{BUNDLE_SMOKE_JOB_DIR}"'
        ),
        "task_command_template": (
            f'python "{BUNDLE_TASK_SCRIPT}" --input-dir "F:\\bio-script\\outputs\\tasks\\ncbi_bundle" '
            f'--job-dir "{BUNDLE_DEFAULT_JOB_DIR}"'
        ),
        "long_running": False,
        "result_reporting_template": [
            "script used",
            "input fasta or ncbi bundle dir",
            "job directory",
            "mrslpred result csv path",
            "mrslpred figure png path",
            "mrslpred figure pdf path",
            "errors file presence",
            "sequence hit count",
        ],
    },
}

DELEGATION_NOTES = {
    "background": (
        "This package wraps the GitHub standalone release of mRSLPred instead of the currently unstable public web server."
    ),
    "long_task_policy": {
        "delegate_to_subagent": True,
        "batch_input_requires_subagent": True,
        "main_thread_waits_to_completion": False,
        "main_thread_default_reply": [
            "delegated",
            "subagent name",
            "execution command",
            "output path",
        ],
        "query_results_later": True,
        "stop_on_user_request": True,
    },
    "workflow": [
        "Read README.md, COMMANDS.md, and manifest.py before executing.",
        "Verify the compatible conda environment exists before formal execution.",
        "Run the help command or a smoke command first.",
        "Only after a successful smoke run should you attempt a larger task.",
        "Preserve transcript_accession_version <-> gene_symbol mapping from the FASTA headers.",
        "Use the bundle task when the user wants the prefixed mRSLPred result table and presentation-style image outputs.",
    ],
    "must_include": [
        "GitHub source URL",
        "runtime environment requirement",
        "input FASTA path",
        "recommended command",
        "mapping preservation rule",
    ],
    "do_not": [
        "Do not call the broken web server when the standalone runtime is available.",
        "Do not drop transcript or gene metadata from the FASTA headers.",
        "Do not run mRSLPred in the current Python 3.14 environment.",
        "Do not expose the deprecated split tasks as user-facing entrypoints.",
    ],
}
