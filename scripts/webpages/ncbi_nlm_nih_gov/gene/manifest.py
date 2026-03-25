"""Machine-readable metadata for the NCBI gene package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
GENE_SET_TO_FASTA_BUNDLE_TASK_SCRIPT = PAGE_DIR / "tasks" / "gene_set_to_fasta_bundle.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
GENE_SET_TO_FASTA_BUNDLE_DEFAULT_JOB_DIR = (
    ROOT / "outputs" / "tasks" / "GeneSeq_NCBI_GeneBundle_human_default"
)
GENE_SET_TO_FASTA_BUNDLE_SMOKE_JOB_DIR = (
    ROOT / "outputs" / "tasks" / "GeneSeq_NCBI_GeneBundle_human_smoke_PIK3CA"
)

PAGE_METADATA = {
    "page_key": "ncbi_nlm_nih_gov.gene",
    "homepage": "https://www.ncbi.nlm.nih.gov/",
    "page_type": "webpage",
    "interaction_mode": "api",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "gene_set_to_fasta_bundle": {
        "task_key": "gene_set_to_fasta_bundle",
        "bio_category": "mRNA",
        "bio_goal": "gene symbol -> recommended-transcript sequence bundle",
        "description": "Resolve gene symbols, keep all/recommended transcripts, and fetch FASTA for the recommended transcript of each matched gene.",
        "entrypoint_script": str(GENE_SET_TO_FASTA_BUNDLE_TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(GENE_SET_TO_FASTA_BUNDLE_DEFAULT_JOB_DIR),
        "master_file_name": "recommended_transcripts.fasta",
        "master_file_mode": "multi_file_bundle",
        "master_file_is_concatenated": False,
        "master_file_required_columns": [],
        "required_output_files": [
            "recommended_transcripts.csv",
            "recommended_transcripts.fasta",
        ],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "test_output_cleanup_scope": (
            "Delete smoke/test job directories after verification unless the user explicitly asks to keep them."
        ),
        "help_command": f'python "{GENE_SET_TO_FASTA_BUNDLE_TASK_SCRIPT}" --help',
        "smoke_command": (
            f'python "{GENE_SET_TO_FASTA_BUNDLE_TASK_SCRIPT}" --gene PIK3CA '
            f'--job-dir "{GENE_SET_TO_FASTA_BUNDLE_SMOKE_JOB_DIR}"'
        ),
        "task_command_template": (
            f'python "{GENE_SET_TO_FASTA_BUNDLE_TASK_SCRIPT}" --input "F:\\bio-script\\data\\biomarker_genes.txt" '
            f'--job-dir "{GENE_SET_TO_FASTA_BUNDLE_DEFAULT_JOB_DIR}"'
        ),
        "long_running": False,
        "result_reporting_template": [
            "script used",
            "input file",
            "job directory",
            "all transcripts file path",
            "recommended transcripts file path",
            "recommended transcript FASTA records file path",
            "fasta path",
            "errors file presence",
            "matched gene count",
            "recommended transcript row count",
        ],
    },
}

DELEGATION_NOTES = {
    "background": (
        "This package uses NCBI Datasets product reports for transcript resolution and NCBI EFetch for FASTA retrieval."
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
        "Run the help command or smoke command first.",
        "Only after a successful smoke run should you attempt a larger task.",
        "Delete smoke/test outputs after verification unless the user explicitly asks to keep them.",
        "Preserve gene_symbol <-> transcript mappings in the combined bundle.",
    ],
    "must_include": [
        "background information",
        "task goal",
        "recommended command",
        "smoke/test command",
        "mapping preservation rule",
    ],
    "do_not": [
        "Do not introduce cross-webpage common helpers.",
        "Do not run long batch jobs by default.",
        "Do not keep smoke/test output directories after validation unless the user explicitly asks to keep them.",
        "Do not expose the deprecated split tasks as user-facing entrypoints.",
    ],
}
