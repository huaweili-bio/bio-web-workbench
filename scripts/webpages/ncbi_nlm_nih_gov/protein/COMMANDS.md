# NCBI protein command templates

All commands below assume PowerShell on Windows.

## help

### `gene_set_to_protein_bundle`

```powershell
python "scripts\webpages\ncbi_nlm_nih_gov\protein\tasks\gene_set_to_protein_bundle.py" --help
```

## smoke

### `gene_set_to_protein_bundle`

```powershell
python "scripts\protocol_gate.py" --page-key ncbi_nlm_nih_gov.protein --task-key gene_set_to_protein_bundle --query-count 1 --execution-mode main_thread --current-boundary "This turn only validates the one-step NCBI protein bundle path. Do not run UniProt, CELLO, or Cell-PLoc." --job-dir "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__smoke_TP53" --output "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__smoke_TP53\protocol_check.json"
python "scripts\webpages\ncbi_nlm_nih_gov\protein\tasks\gene_set_to_protein_bundle.py" --gene TP53 --job-dir "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__smoke_TP53" --protocol-check-file "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__smoke_TP53\protocol_check.json"
```

## task

### `gene_set_to_protein_bundle`

```powershell
python "scripts\protocol_gate.py" --page-key ncbi_nlm_nih_gov.protein --task-key gene_set_to_protein_bundle --input-file "data\biomarker_genes.txt" --execution-mode delegated_subagent --subagent-name NcbiProteinBundleWorker --current-boundary "This turn only prepares the one-step NCBI protein bundle with all proteins, recommended proteins, and FASTA files for downstream protein localization." --job-dir "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__custom_batch" --output "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__custom_batch\protocol_check.json"
python "scripts\webpages\ncbi_nlm_nih_gov\protein\tasks\gene_set_to_protein_bundle.py" --input "data\biomarker_genes.txt" --job-dir "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__custom_batch" --protocol-check-file "outputs\tasks\ncbi_nlm_nih_gov__protein__gene_set_to_protein_bundle__human__custom_batch\protocol_check.json"
```

## long-running

- Batch gene files require delegation under the current protocol.
- Formal runs must go through `scripts\protocol_gate.py` first.
- This bundle is the preferred upstream output for protein localization tasks.
