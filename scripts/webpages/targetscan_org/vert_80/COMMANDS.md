# TargetScanHuman 8.0 command templates

## help

```powershell
python "scripts\webpages\targetscan_org\vert_80\tasks\mrna_to_mirna.py" --help
```

## smoke

```powershell
python "scripts\protocol_gate.py" --page-key targetscan_org.vert_80 --task-key mrna_to_mirna --query-count 1 --execution-mode main_thread --current-boundary "This turn only runs a single TargetScanHuman smoke check." --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_smoke_APP" --output "outputs\tasks\mRNA_miRNA_TargetScan_smoke_APP\protocol_check.json"
python "scripts\webpages\targetscan_org\vert_80\tasks\mrna_to_mirna.py" --gene APP --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_smoke_APP" --protocol-check-file "outputs\tasks\mRNA_miRNA_TargetScan_smoke_APP\protocol_check.json"
```

If the smoke directory is only for validation, delete it afterwards:

```powershell
Remove-Item -Recurse -Force "outputs\tasks\mRNA_miRNA_TargetScan_smoke_APP"
```

## task

```powershell
python "scripts\protocol_gate.py" --page-key targetscan_org.vert_80 --task-key mrna_to_mirna --input-file "data\biomarker_genes.txt" --execution-mode delegated_subagent --subagent-name TargetScanWorker --current-boundary "This turn only runs a single-database TargetScanHuman batch query for mature miRNA predicted target details." --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch" --output "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch\protocol_check.json"
python "scripts\webpages\targetscan_org\vert_80\tasks\mrna_to_mirna.py" --input "data\biomarker_genes.txt" --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch" --protocol-check-file "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch\protocol_check.json"
```

## task with local mode

```powershell
python "scripts\protocol_gate.py" --page-key targetscan_org.vert_80 --task-key mrna_to_mirna --input-file "data\biomarker_genes.txt" --execution-mode delegated_subagent --subagent-name TargetScanWorker --current-boundary "This turn only runs a single-database TargetScanHuman batch query in local-mode using predownloaded score ZIP files." --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch" --output "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch\protocol_check.json"
python "scripts\webpages\targetscan_org\vert_80\tasks\mrna_to_mirna.py" --input "data\biomarker_genes.txt" --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch" --local-mode --local-data-dir "scripts\webpages\targetscan_org\vert_80\local_data" --protocol-check-file "outputs\tasks\mRNA_miRNA_TargetScan_custom_batch\protocol_check.json"
```

## debug

```powershell
python "scripts\webpages\targetscan_org\vert_80\tasks\mrna_to_mirna.py" --help
python "scripts\protocol_gate.py" --page-key targetscan_org.vert_80 --task-key mrna_to_mirna --query-count 1 --execution-mode main_thread --current-boundary "This turn only runs a single TargetScanHuman debug query." --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_debug_single_query" --output "outputs\tasks\mRNA_miRNA_TargetScan_debug_single_query\protocol_check.json"
python "scripts\webpages\targetscan_org\vert_80\tasks\mrna_to_mirna.py" --gene APP --job-dir "outputs\tasks\mRNA_miRNA_TargetScan_debug_single_query" --protocol-check-file "outputs\tasks\mRNA_miRNA_TargetScan_debug_single_query\protocol_check.json"
```

## long-running

- Formal execution always requires `--protocol-check-file`.
- Batch gene inputs must be delegated to a subagent.
- The first full run may be slow because TargetScan cache initialization downloads multiple official ZIP files, including very large nonconserved all-predictions tables.
- `--local-mode` avoids downloading the two large score ZIP files and instead reads them from `local_data/`.
- In `--local-mode`, the task first checks local file sizes against the official webpage size when available. If the official file is larger, the task stops and reminds the user to refresh the local file.

## output contract

- Keep only `targetscanhuman_result.csv` at the job-dir root.
- Keep protocol, summary, copied input files, and other diagnostics under `temp/`.
