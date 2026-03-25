# NCBI gene/transcript preparation

Page and API entry points:

- `https://www.ncbi.nlm.nih.gov/`
- `https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/`
- `https://www.ncbi.nlm.nih.gov/books/NBK25501/`

## Purpose

This package prepares one NCBI output folder for downstream sequence-based tasks.
It keeps the full transcript view, the recommended transcript view, and the recommended-transcript FASTA in the same directory.

## Implemented task

- `gene_set_to_fasta_bundle`
  - Input: one or more gene symbols from repeated `--gene`, text input, or CSV input
  - Output:
    - `query_genes.txt`
    - `all_transcripts.csv`
    - `recommended_transcripts.csv`
    - `recommended_transcript_fasta_records.csv`
    - `recommended_transcripts.fasta`
    - `summary.json`
    - optional `errors.json`
    - `temp/`
  - Behavior:
    - resolves all transcripts for each gene via NCBI Datasets `product_report`
    - ranks transcripts and keeps one recommended transcript per matched gene
    - fetches FASTA only for the recommended transcript of each matched gene
    - preserves `gene_symbol <-> transcript_accession_version <-> fasta_header`

## Transcript ranking rule

Recommended transcripts are chosen by the following priority:

1. `MANE_SELECT`
2. `MANE_PLUS_CLINICAL`
3. `REFSEQ_SELECT`
4. RefSeq accession priority: `NM_` > `NR_` > `XM_` > `XR_`
5. longer transcript length
6. accession lexical order as a final tie-breaker

## Current boundary

This package only covers:

- `gene set -> recommended-transcript sequence bundle`

This package does not cover:

- `mRSLPred`
- subcellular localization
- subcellular localization plotting
- cross-database consensus or network analysis

## Output contract

Each formal run writes one NCBI bundle directory:

- `query_genes.txt`
- `all_transcripts.csv`
- `recommended_transcripts.csv`
- `recommended_transcript_fasta_records.csv`
- `recommended_transcripts.fasta`
- `summary.json`
- optional `errors.json`
- `temp/`

`temp/` is reserved for copied inputs, normalized inputs, raw JSON/FASTA responses, and other execution artifacts.

## Notes

- Formal runs require `--protocol-check-file`.
- This is now the only user-facing NCBI task in this package.
- `recommended_transcript_fasta_records.csv` and `recommended_transcripts.fasta` always correspond to the recommended transcript set.
