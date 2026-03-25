"""Machine-readable metadata for the NCBI protein package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
TASK_SCRIPT = PAGE_DIR / "tasks" / "gene_set_to_protein_bundle.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "ProteinSeq_NCBI_ProteinBundle_default"

PAGE_METADATA = {
    "page_key": "ncbi_nlm_nih_gov.protein",
    "homepage": "https://www.ncbi.nlm.nih.gov/",
    "page_type": "webpage",
    "interaction_mode": "api",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "gene_set_to_protein_bundle": {
        "task_key": "gene_set_to_protein_bundle",
        "bio_category": "protein",
        "bio_goal": "gene symbol -> recommended-protein sequence bundle",
        "description": "Resolve all protein-bearing NCBI products, keep one recommended protein per gene, and fetch protein FASTA for downstream analysis tasks.",
        "entrypoint_script": str(TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(DEFAULT_JOB_DIR),
        "master_file_name": "recommended_proteins.fasta",
        "master_file_mode": "multi_file_bundle",
        "master_file_is_concatenated": False,
        "master_file_required_columns": [
            "query_gene_symbol",
            "gene_symbol",
            "protein_accession_version",
            "protein_name",
        ],
        "required_output_files": [
            "recommended_proteins.csv",
            "recommended_proteins.fasta",
        ],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "help_command": f'python "{TASK_SCRIPT}" --help',
        "task_command_template": f'python "{TASK_SCRIPT}" --gene TP53 --job-dir "{DEFAULT_JOB_DIR}"',
        "long_running": False,
    },
}
