# mRSLPred command templates

All commands below assume PowerShell on Windows.

## help

### `fasta_to_localization_bundle`

```powershell
python "scripts\webpages\github_com\raghavagps_mrslpred\tasks\fasta_to_localization_bundle.py" --help
```

## smoke

### `fasta_to_localization_bundle`

```powershell
python "scripts\protocol_gate.py" --page-key github_com.raghavagps_mrslpred --task-key fasta_to_localization_bundle --input-file "data\mrslpred_smoke.fasta" --execution-mode delegated_subagent --subagent-name MrslpredBundleWorker --current-boundary "This turn only validates the one-step mRSLPred bundle path and does not rerun upstream NCBI preparation." --job-dir "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__smoke" --output "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__smoke\protocol_check.json"
python "scripts\webpages\github_com\raghavagps_mrslpred\tasks\fasta_to_localization_bundle.py" --input "data\mrslpred_smoke.fasta" --job-dir "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__smoke" --protocol-check-file "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__smoke\protocol_check.json"
```

## task

### `fasta_to_localization_bundle`

```powershell
python "scripts\protocol_gate.py" --page-key github_com.raghavagps_mrslpred --task-key fasta_to_localization_bundle --input-file "outputs\tasks\ncbi_bundle\recommended_transcripts.fasta" --execution-mode delegated_subagent --subagent-name MrslpredBundleWorker --current-boundary "This turn only runs the one-step mRSLPred bundle on an existing FASTA input and emits prediction plus PNG/PDF." --job-dir "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__custom" --output "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__custom\protocol_check.json"
python "scripts\webpages\github_com\raghavagps_mrslpred\tasks\fasta_to_localization_bundle.py" --input-dir "outputs\tasks\ncbi_bundle" --job-dir "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__custom" --protocol-check-file "outputs\tasks\github_com__raghavagps_mrslpred__fasta_to_localization_bundle__custom\protocol_check.json"
```

## debug

### `fasta_to_localization_bundle`

```powershell
python "scripts\webpages\github_com\raghavagps_mrslpred\tasks\fasta_to_localization_bundle.py" --help
```

## long-running

- Batch FASTA input requires delegation under the current protocol.
- Formal runs must go through `scripts\protocol_gate.py` first.
- The default runtime assumes a compatible conda environment named `mrslpred_py37`.
- If that environment is missing, create it before formal execution.

## output contract

- `mrslpred_result.csv`
- `mrslpred_localization_figure.png`
- `mrslpred_localization_figure.pdf`
- `summary.json`
- optional `errors.json`
- `temp/`
