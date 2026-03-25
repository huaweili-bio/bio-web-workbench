# TargetScanHuman 8.0

Homepage: `https://www.targetscan.org/vert_80/`

## Current task

- `mrna_to_mirna`
  - Input: one or more human biomarker gene symbols from inline flags, text files, or CSV files
  - Output: `targetscanhuman_result.csv`, `temp/summary.json`, optional `temp/errors.json`, and `temp/`
  - Goal: export mature miRNA predicted target details for each queried gene
  - Source tables:
    - `miR_Family_Info.txt.zip`
    - `Conserved_Family_Info.txt.zip`
    - `Nonconserved_Family_Info.txt.zip`
    - `Conserved_Site_Context_Scores.txt.zip`
    - `Nonconserved_Site_Context_Scores.txt.zip`
  - Local mode: `--local-mode` uses predownloaded `Conserved_Site_Context_Scores.txt.zip` and `Nonconserved_Site_Context_Scores.txt.zip` from `local_data/`, while the three smaller helper archives still use cache/download mode
  - Local mode safety rule: before execution, the task compares local file sizes against the official webpage size when that remote size can be queried; if the official file is larger, the task fails closed and asks the user to refresh the local file
  - Granularity: one mature miRNA site prediction per row, not miRNA family summary rows
  - Transcript scope: representative transcripts from official all-predictions tables
  - Top-level output contract: only `targetscanhuman_result.csv` is kept at the job-dir root; protocol, summary, copied inputs, and other diagnostics stay under `temp/`

## Boundaries

- This webpage package only implements TargetScanHuman 8.0 single-database querying.
- It accepts already-known human biomarker gene symbols.
- It does not discover biomarkers from literature.
- It does not perform cross-database intersection, ranking, or downstream reporting outside this webpage package.

## Execution rules

- Read `README.md`, `COMMANDS.md`, and `manifest.py` before execution.
- Formal execution requires `scripts\protocol_gate.py` and `--protocol-check-file`.
- Batch file inputs must be delegated to a subagent.
- If the official download of the two large score archives is unstable, use `--local-mode`.
- In `--local-mode`, remote size checks are attempted first. A larger official file is treated as a likely update and stops execution with a reminder.
- Smoke/test output directories should be deleted after verification unless the user explicitly asks to keep them.

## Cache note

- The first real run may initialize a large TargetScan cache because the task downloads multiple official ZIP files.
- The largest archives are the nonconserved all-predictions tables, so first-run startup can be much slower than subsequent runs.
