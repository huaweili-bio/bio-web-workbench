"""Machine-readable metadata for the ENCORI webpage package."""

from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PAGE_DIR.parents[2]
ROOT = SCRIPTS_DIR.parent
TASK_SCRIPT = PAGE_DIR / "tasks" / "mirna_to_lncrna.py"
MRNA_TO_MIRNA_TASK_SCRIPT = PAGE_DIR / "tasks" / "mrna_to_mirna.py"
COMMANDS_DOC = PAGE_DIR / "COMMANDS.md"
README_DOC = PAGE_DIR / "README.md"
DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "miRNA_lncRNA_ENCORI_hg38_default"
SMOKE_JOB_DIR = ROOT / "outputs" / "tasks" / "miRNA_lncRNA_ENCORI_hg38_smoke_hsa_miR_21_5p"
MRNA_TO_MIRNA_DEFAULT_JOB_DIR = ROOT / "outputs" / "tasks" / "mRNA_miRNA_ENCORI_hg38_default"
MRNA_TO_MIRNA_SMOKE_JOB_DIR = ROOT / "outputs" / "tasks" / "mRNA_miRNA_ENCORI_hg38_smoke_PIK3CA"

PAGE_METADATA = {
    "page_key": "rnasysu_com.encori",
    "homepage": "https://rnasysu.com/encori/",
    "page_type": "webpage",
    "interaction_mode": "api",
    "status": "active",
    "code_root": str(PAGE_DIR),
    "readme": str(README_DOC),
    "commands_doc": str(COMMANDS_DOC),
}

TASKS = {
    "mirna_to_lncrna": {
        "task_key": "mirna_to_lncrna",
        "bio_category": "miRNA",
        "bio_goal": "miRNA -> lncRNA targets",
        "description": "Query ENCORI by miRNA and export lncRNA interaction results.",
        "entrypoint_script": str(TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(DEFAULT_JOB_DIR),
        "master_file_name": "encori_result.csv",
        "master_file_mode": "direct_generated_master_file",
        "master_file_is_concatenated": False,
        "master_file_required_columns": ["query_mirna", "query_lncrna_count", "geneName"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "test_output_cleanup_scope": (
            "Delete smoke/test job directories after verification unless the user explicitly asks to keep them."
        ),
        "help_command": f'python "{TASK_SCRIPT}" --help',
        "smoke_command": (
            f'python "{TASK_SCRIPT}" --mirna hsa-miR-21-5p '
            f'--job-dir "{SMOKE_JOB_DIR}"'
        ),
        "task_command_template": (
            f'python "{TASK_SCRIPT}" --input "F:\\bio-script\\data\\mirnas.txt" '
            f'--job-dir "{DEFAULT_JOB_DIR}"'
        ),
        "long_running": False,
        "result_reporting_template": [
            "script used",
            "input file",
            "master file mode",
            "job directory",
            "master file path",
            "errors file presence",
            "miRNA hit count",
            "final row count",
        ],
    },
    "mrna_to_mirna": {
        "task_key": "mrna_to_mirna",
        "bio_category": "mRNA",
        "bio_goal": "mRNA biomarker -> miRNA targets",
        "description": "Query ENCORI by gene symbol and export miRNA-mRNA interaction results.",
        "entrypoint_script": str(MRNA_TO_MIRNA_TASK_SCRIPT),
        "preferred_output_mode": "job_dir",
        "default_job_dir": str(MRNA_TO_MIRNA_DEFAULT_JOB_DIR),
        "master_file_name": "encori_result.csv",
        "master_file_mode": "direct_generated_master_file",
        "master_file_is_concatenated": False,
        "master_file_required_columns": ["query_gene_symbol", "query_mirna_count", "miRNAname"],
        "temp_dir_name": "temp",
        "protocol_check_required": True,
        "batch_input_requires_subagent": True,
        "test_output_cleanup_required": True,
        "avoid_explicit_timeout_parameter": True,
        "test_output_cleanup_scope": (
            "Delete smoke/test job directories after verification unless the user explicitly asks to keep them."
        ),
        "help_command": f'python "{MRNA_TO_MIRNA_TASK_SCRIPT}" --help',
        "smoke_command": (
            f'python "{MRNA_TO_MIRNA_TASK_SCRIPT}" --gene PIK3CA '
            f'--job-dir "{MRNA_TO_MIRNA_SMOKE_JOB_DIR}"'
        ),
        "task_command_template": (
            f'python "{MRNA_TO_MIRNA_TASK_SCRIPT}" --input "F:\\bio-script\\data\\biomarker_genes.txt" '
            f'--job-dir "{MRNA_TO_MIRNA_DEFAULT_JOB_DIR}"'
        ),
        "long_running": False,
        "result_reporting_template": [
            "script used",
            "input file",
            "master file mode",
            "job directory",
            "master file path",
            "errors file presence",
            "gene hit count",
            "final row count",
        ],
    },
}

DELEGATION_NOTES = {
    "background": (
        "This page is backed by ENCORI official tab-delimited API endpoints. "
        "The implemented tasks query either miRNA -> lncRNA interactions or mRNA -> miRNA interactions."
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
        "Avoid specifying --timeout explicitly unless the user asks for it or debugging requires it.",
    ],
    "must_include": [
        "background information",
        "task goal",
        "recommended command",
        "smoke/test command",
        "forbidden long-running behavior",
    ],
    "do_not": [
        "Do not introduce cross-webpage common helpers.",
        "Do not run long batch jobs by default.",
        "Do not keep smoke/test output directories after validation unless the user explicitly asks to keep them.",
        "Do not add explicit --timeout to routine commands unless the user asks for it or debugging requires it.",
        "Do not call LncBase from this webpage package.",
        "Do not implement intersection, consensus, or specificity filtering tasks in this webpage package.",
    ],
}
