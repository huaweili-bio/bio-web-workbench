# Quickstart

This repository is organized around small, reproducible task scripts.

## Requirements

- Python 3.11 or newer
- Internet access for tasks that query online resources
- PowerShell examples are provided, but the entrypoints are standard Python scripts

## Basic Workflow

1. Pick a webpage package under `scripts/webpages/`
2. Read that package's `README.md`, `COMMANDS.md`, and `manifest.py`
3. Create a protocol check file with `scripts/protocol_gate.py`
4. Run the task script with `--protocol-check-file`

## Example Pattern

```powershell
python "scripts/protocol_gate.py" --page-key <page_key> --task-key <task_key> --query-count 1 --execution-mode main_thread --current-boundary "Run one formal task only." --job-dir "outputs/tasks/demo_job" --output "outputs/tasks/demo_job/protocol_check.json"
python "scripts/webpages/<package>/tasks/<task>.py" --job-dir "outputs/tasks/demo_job" --protocol-check-file "outputs/tasks/demo_job/protocol_check.json"
```

## Notes

- Generated outputs are intentionally local-only and are ignored by Git.
- Some tasks depend on public websites or public download endpoints that may change over time.
- Large third-party archives, such as local `TargetScan` bundles, are not redistributed in the public snapshot.
