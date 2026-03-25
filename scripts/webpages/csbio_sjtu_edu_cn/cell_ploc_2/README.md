# Cell-PLoc 2.0 human protein localization prediction

Page entry points:

- `http://www.csbio.sjtu.edu.cn/bioinf/Cell-PLoc-2/`
- `http://www.csbio.sjtu.edu.cn/cgi-bin/HummPLoc2.cgi`

## Purpose

This package submits human protein FASTA records to Cell-PLoc 2.0 and captures per-sequence localization predictions.

## Implemented task

- `human_protein_fasta_to_localization`
  - Input: human protein FASTA file
  - Output:
    - `protein_localization_result.csv`
    - `raw_response.html`
    - `summary.json`
    - optional `errors.json`
  - Behavior:
    - submits each FASTA record to the human multi-label Cell-PLoc 2.0 form
    - parses predicted localization text from the returned HTML
    - stores one result row per FASTA record

## Current boundary

This package only covers:

- `human protein FASTA -> Cell-PLoc localization prediction`

This package does not cover:

- other organism branches
- sequence download
- cross-method consensus
