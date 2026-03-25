# CELLO command templates

All commands below assume PowerShell on Windows.

## help

### `protein_fasta_to_localization`

```powershell
python "scripts\webpages\cello_life_nctu_edu_tw\root\tasks\protein_fasta_to_localization.py" --help
```

### `protein_fasta_to_localization` with coding nucleotide input

```powershell
python "scripts\webpages\cello_life_nctu_edu_tw\root\tasks\protein_fasta_to_localization.py" --input "data\your_coding_sequences.fasta" --seqtype dna --job-dir "outputs\tasks\ProteinLoc_CELLO_DNA_example" --protocol-check-file "outputs\tasks\ProteinLoc_CELLO_DNA_example\protocol_check.json"
```
