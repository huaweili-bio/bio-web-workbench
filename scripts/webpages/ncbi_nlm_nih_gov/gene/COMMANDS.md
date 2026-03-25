# NCBI command templates

All commands below assume PowerShell on Windows.

## help

### `gene_set_to_fasta_bundle`

```powershell
python "scripts\webpages\ncbi_nlm_nih_gov\gene\tasks\gene_set_to_fasta_bundle.py" --help
```

## smoke

### `gene_set_to_fasta_bundle`

```powershell
python "scripts\protocol_gate.py" --page-key ncbi_nlm_nih_gov.gene --task-key gene_set_to_fasta_bundle --query-count 1 --execution-mode main_thread --current-boundary "This turn only validates the one-step NCBI gene-set to FASTA bundle path. Do not run mRSLPred." --job-dir "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__smoke_PIK3CA" --output "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__smoke_PIK3CA\protocol_check.json"
python "scripts\webpages\ncbi_nlm_nih_gov\gene\tasks\gene_set_to_fasta_bundle.py" --gene PIK3CA --job-dir "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__smoke_PIK3CA" --protocol-check-file "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__smoke_PIK3CA\protocol_check.json"
```

## task

### `gene_set_to_fasta_bundle`

```powershell
python "scripts\protocol_gate.py" --page-key ncbi_nlm_nih_gov.gene --task-key gene_set_to_fasta_bundle --input-file "data\biomarker_genes.txt" --execution-mode delegated_subagent --subagent-name NcbiBundleWorker --current-boundary "This turn only prepares the one-step NCBI bundle with all transcripts, recommended transcripts, and FASTA files for downstream mRSLPred." --job-dir "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__custom_batch" --output "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__custom_batch\protocol_check.json"
python "scripts\webpages\ncbi_nlm_nih_gov\gene\tasks\gene_set_to_fasta_bundle.py" --input "data\biomarker_genes.txt" --job-dir "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__custom_batch" --protocol-check-file "outputs\tasks\ncbi_nlm_nih_gov__gene__gene_set_to_fasta_bundle__human__custom_batch\protocol_check.json"
```

## debug

### `gene_set_to_fasta_bundle`

```powershell
python "scripts\webpages\ncbi_nlm_nih_gov\gene\tasks\gene_set_to_fasta_bundle.py" --help
```

## long-running

- Batch gene files still require delegation under the current protocol.
- Formal runs must go through `scripts\protocol_gate.py` first.
- This bundle is the preferred upstream output for `mRSLPred`.

## output contract

- `query_genes.txt`
- `all_transcripts.csv`
- `recommended_transcripts.csv`
- `recommended_transcript_fasta_records.csv`
- `recommended_transcripts.fasta`
- `summary.json`
- optional `errors.json`
- `temp/`
