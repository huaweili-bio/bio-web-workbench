#!/usr/bin/env python3
"""Fail-closed protocol gate for formal task execution."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from webpages.diana_e_ce_uth_gr.lncbasev3_home.manifest import (
    PAGE_METADATA as LNCBASE_PAGE_METADATA,
    TASKS as LNCBASE_TASKS,
)
from webpages.rnasysu_com.encori.manifest import (
    PAGE_METADATA as ENCORI_PAGE_METADATA,
    TASKS as ENCORI_TASKS,
)
from webpages.ncbi_nlm_nih_gov.gene.manifest import (
    PAGE_METADATA as NCBI_GENE_PAGE_METADATA,
    TASKS as NCBI_GENE_TASKS,
)
from webpages.ncbi_nlm_nih_gov.protein.manifest import (
    PAGE_METADATA as NCBI_PROTEIN_PAGE_METADATA,
    TASKS as NCBI_PROTEIN_TASKS,
)
from webpages.mirdb_org.index.manifest import (
    PAGE_METADATA as MIRDB_PAGE_METADATA,
    TASKS as MIRDB_TASKS,
)
from webpages.targetscan_org.vert_80.manifest import (
    PAGE_METADATA as TARGETSCAN_PAGE_METADATA,
    TASKS as TARGETSCAN_TASKS,
)
from webpages.genemania_org.search.manifest import (
    PAGE_METADATA as GENEMANIA_PAGE_METADATA,
    TASKS as GENEMANIA_TASKS,
)
from webpages.github_com.raghavagps_mrslpred.manifest import (
    PAGE_METADATA as MRSLPRED_PAGE_METADATA,
    TASKS as MRSLPRED_TASKS,
)
from webpages.uniprot_org.uniprotkb.manifest import (
    PAGE_METADATA as UNIPROT_PAGE_METADATA,
    TASKS as UNIPROT_TASKS,
)
from webpages.cello_life_nctu_edu_tw.root.manifest import (
    PAGE_METADATA as CELLO_PAGE_METADATA,
    TASKS as CELLO_TASKS,
)
from webpages.csbio_sjtu_edu_cn.cell_ploc_2.manifest import (
    PAGE_METADATA as CELL_PLOC_PAGE_METADATA,
    TASKS as CELL_PLOC_TASKS,
)
from webpages.rnalocate_org.search.manifest import (
    PAGE_METADATA as RNALOCATE_PAGE_METADATA,
    TASKS as RNALOCATE_TASKS,
)


def _build_registry() -> dict[tuple[str, str], dict[str, Any]]:
    registry: dict[tuple[str, str], dict[str, Any]] = {}

    for page_metadata, tasks in (
        (LNCBASE_PAGE_METADATA, LNCBASE_TASKS),
        (ENCORI_PAGE_METADATA, ENCORI_TASKS),
        (NCBI_GENE_PAGE_METADATA, NCBI_GENE_TASKS),
        (NCBI_PROTEIN_PAGE_METADATA, NCBI_PROTEIN_TASKS),
        (MIRDB_PAGE_METADATA, MIRDB_TASKS),
        (TARGETSCAN_PAGE_METADATA, TARGETSCAN_TASKS),
        (GENEMANIA_PAGE_METADATA, GENEMANIA_TASKS),
        (MRSLPRED_PAGE_METADATA, MRSLPRED_TASKS),
        (UNIPROT_PAGE_METADATA, UNIPROT_TASKS),
        (CELLO_PAGE_METADATA, CELLO_TASKS),
        (CELL_PLOC_PAGE_METADATA, CELL_PLOC_TASKS),
        (RNALOCATE_PAGE_METADATA, RNALOCATE_TASKS),
    ):
        page_key = str(page_metadata["page_key"])
        for task_key, task_metadata in tasks.items():
            registry[(page_key, task_key)] = {
                "page_key": page_key,
                "page_homepage": page_metadata["homepage"],
                "page_code_root": page_metadata["code_root"],
                "task_key": task_key,
                "task_entrypoint_script": task_metadata["entrypoint_script"],
                "task_description": task_metadata["description"],
                "batch_input_requires_subagent": bool(task_metadata["batch_input_requires_subagent"]),
            }
    return registry


REGISTRY = _build_registry()


class ProtocolGateError(ValueError):
    """Raised when protocol gate metadata is missing or invalid."""


def infer_input_type(
    *,
    mirna_count: int | None = None,
    query_count: int | None = None,
    input_file: Path | None,
) -> str:
    if input_file is not None:
        return "batch_file"

    if mirna_count is not None and query_count is not None:
        raise ProtocolGateError("Use either --mirna-count or --query-count, not both.")

    resolved_count = mirna_count if mirna_count is not None else query_count
    if resolved_count is None:
        raise ProtocolGateError("Provide --mirna-count or --query-count for inline inputs.")
    if resolved_count < 1:
        raise ProtocolGateError("--mirna-count/--query-count must be at least 1.")
    if resolved_count == 1:
        return "single_inline"
    return "batch_inline"


def create_protocol_ticket(
    *,
    page_key: str,
    task_key: str,
    execution_mode: str,
    subagent_name: str,
    current_boundary: str,
    mirna_count: int | None = None,
    query_count: int | None = None,
    input_file: Path | None = None,
    job_dir: Path | None = None,
) -> dict[str, Any]:
    registry_key = (page_key, task_key)
    if registry_key not in REGISTRY:
        known = ", ".join(f"{known_page}:{known_task}" for known_page, known_task in sorted(REGISTRY))
        raise ProtocolGateError(
            f"Unknown page/task combination '{page_key}:{task_key}'. Known combinations: {known}"
        )

    current_boundary = current_boundary.strip()
    if len(current_boundary) < 8:
        raise ProtocolGateError("--current-boundary is too short. State what this round will do and will not do.")

    subagent_name = subagent_name.strip()
    input_type = infer_input_type(mirna_count=mirna_count, query_count=query_count, input_file=input_file)
    task_metadata = REGISTRY[registry_key]
    batch_requires_subagent = bool(task_metadata["batch_input_requires_subagent"])
    is_batch = input_type != "single_inline"
    resolved_count = mirna_count if mirna_count is not None else query_count

    if input_file is not None and not input_file.exists():
        raise ProtocolGateError(f"Input file does not exist: {input_file}")

    if execution_mode not in {"main_thread", "delegated_subagent"}:
        raise ProtocolGateError("--execution-mode must be 'main_thread' or 'delegated_subagent'.")

    if execution_mode == "delegated_subagent" and not subagent_name:
        raise ProtocolGateError("--subagent-name is required when --execution-mode delegated_subagent is used.")

    if is_batch and batch_requires_subagent and execution_mode != "delegated_subagent":
        raise ProtocolGateError(
            "This task treats the current input as batch, and batch execution must be delegated to a subagent."
        )

    if job_dir is not None and not job_dir.is_absolute():
        raise ProtocolGateError("--job-dir must be an absolute path.")

    return {
        "approved": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "page_key": page_key,
        "page_homepage": task_metadata["page_homepage"],
        "page_code_root": task_metadata["page_code_root"],
        "task_key": task_key,
        "task_description": task_metadata["task_description"],
        "task_entrypoint_script": task_metadata["task_entrypoint_script"],
        "input_type": input_type,
        "mirna_count": resolved_count or 0,
        "query_count": resolved_count or 0,
        "input_file": str(input_file.resolve()) if input_file is not None else "",
        "execution_mode": execution_mode,
        "subagent_name": subagent_name,
        "main_thread_formal_task_blocked": is_batch and batch_requires_subagent,
        "current_boundary": current_boundary,
        "job_dir": str(job_dir.resolve()) if job_dir is not None else "",
    }


def write_protocol_ticket(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_protocol_ticket(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProtocolGateError(f"Protocol check file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolGateError(f"Protocol check file is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise ProtocolGateError("Protocol check file must contain a JSON object.")
    if payload.get("approved") is not True:
        raise ProtocolGateError("Protocol check file is not approved.")
    return payload


def validate_protocol_ticket(
    path: Path,
    *,
    page_key: str,
    task_key: str,
    input_type: str,
    job_dir: Path | None,
) -> dict[str, Any]:
    payload = load_protocol_ticket(path)
    if payload.get("page_key") != page_key:
        raise ProtocolGateError(
            f"Protocol check page mismatch: expected '{page_key}', got '{payload.get('page_key')}'."
        )
    if payload.get("task_key") != task_key:
        raise ProtocolGateError(
            f"Protocol check task mismatch: expected '{task_key}', got '{payload.get('task_key')}'."
        )
    if payload.get("input_type") != input_type:
        raise ProtocolGateError(
            f"Protocol check input type mismatch: expected '{input_type}', got '{payload.get('input_type')}'."
        )

    registry_key = (page_key, task_key)
    if registry_key not in REGISTRY:
        raise ProtocolGateError(f"Unknown page/task combination '{page_key}:{task_key}' during validation.")
    task_metadata = REGISTRY[registry_key]
    batch_requires_subagent = bool(task_metadata["batch_input_requires_subagent"])

    recorded_job_dir = str(payload.get("job_dir") or "").strip()
    if job_dir is not None:
        if not recorded_job_dir:
            raise ProtocolGateError("Protocol check file does not record a job directory.")
        if Path(recorded_job_dir).resolve() != job_dir.resolve():
            raise ProtocolGateError(
                f"Protocol check job dir mismatch: expected '{job_dir}', got '{recorded_job_dir}'."
            )

    if input_type != "single_inline" and batch_requires_subagent and payload.get("execution_mode") != "delegated_subagent":
        raise ProtocolGateError(
            "Batch execution is only allowed with execution_mode=delegated_subagent in the protocol check file."
        )
    return payload


def render_protocol_check(payload: dict[str, Any]) -> str:
    if payload["execution_mode"] == "delegated_subagent":
        execution_mode = f"必须委派子智能体（{payload['subagent_name']}）"
    else:
        execution_mode = "主线程可直接执行"

    if payload["main_thread_formal_task_blocked"]:
        main_thread_limit = "禁止主线程直接执行正式批量任务"
    else:
        main_thread_limit = "允许主线程执行，但正式任务仍必须先过协议闸门"

    input_label = {
        "single_inline": "单条",
        "batch_inline": "批量内联",
        "batch_file": "批量文件",
    }[payload["input_type"]]

    return "\n".join(
        [
            "协议检查：",
            f"- 任务归属：{payload['page_homepage']} | {payload['page_code_root']}",
            f"- 输入类型：{input_label}",
            f"- 执行方式：{execution_mode}",
            f"- 主线程限制：{main_thread_limit}",
            f"- 当前边界：{payload['current_boundary']}",
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a fail-closed protocol check file before running a formal webpage task.",
    )
    parser.add_argument("--page-key", required=True, help="Manifest page_key, e.g. rnasysu_com.encori.")
    parser.add_argument("--task-key", required=True, help="Task key, e.g. mirna_to_lncrna.")
    parser.add_argument("--mirna-count", type=int, help="Number of inline miRNA inputs.")
    parser.add_argument("--query-count", type=int, help="Number of inline generic query inputs.")
    parser.add_argument("--input-file", type=Path, help="Absolute path to a batch input file.")
    parser.add_argument(
        "--execution-mode",
        required=True,
        choices=["main_thread", "delegated_subagent"],
        help="Whether the formal task will be run by the main thread or a delegated subagent.",
    )
    parser.add_argument("--subagent-name", default="", help="Required when --execution-mode delegated_subagent.")
    parser.add_argument("--current-boundary", required=True, help="What this round will do and will not do.")
    parser.add_argument("--job-dir", type=Path, help="Absolute output job directory for the formal task.")
    parser.add_argument("--output", type=Path, required=True, help="Where to write the protocol check JSON file.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = create_protocol_ticket(
            page_key=args.page_key,
            task_key=args.task_key,
            mirna_count=args.mirna_count,
            query_count=args.query_count,
            input_file=args.input_file,
            execution_mode=args.execution_mode,
            subagent_name=args.subagent_name,
            current_boundary=args.current_boundary,
            job_dir=args.job_dir,
        )
        write_protocol_ticket(args.output, payload)
    except ProtocolGateError as exc:
        print(str(exc))
        return 2

    print(render_protocol_check(payload))
    print(f"Protocol check file: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
