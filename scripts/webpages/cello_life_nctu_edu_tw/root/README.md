# CELLO protein localization prediction

Page entry points:

- `https://cello.life.nctu.edu.tw/`
- `https://cello.life.nctu.edu.tw/cgi/main.cgi`

## Purpose

This package submits CELLO queries and captures per-sequence protein localization predictions.

## Implemented task

- `protein_fasta_to_localization`
  - Input: protein FASTA by default; coding nucleotide FASTA when `--seqtype dna`
  - Output:
    - `protein_localization_result.csv`
    - `raw_response.html`
    - `summary.json`
    - optional `errors.json`
  - Behavior:
    - submits each FASTA record to CELLO using the live webpage form contract
    - defaults to protein/eukaryote queries
    - supports CELLO DNA mode through `--seqtype dna`
    - when `--seqtype dna` is used, RNA/mRNA-style nucleotides are normalized from `U` to `T` before submission
    - parses predicted localization text from the returned HTML
    - stores one result row per FASTA record

## Current boundary

This package only covers:

- `protein FASTA -> CELLO localization prediction`
- `coding nucleotide FASTA -> protein localization prediction` when `--seqtype dna`

This package does not cover:

- sequence download
- other CELLO species branches
- multi-method consensus
- RNA subcellular localization
