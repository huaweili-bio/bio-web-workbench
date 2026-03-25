# UniProtKB protein localization annotation

Page and API entry points:

- `https://www.uniprot.org/uniprotkb`
- `https://rest.uniprot.org/uniprotkb/search`

## Purpose

This package fetches existing UniProtKB subcellular localization annotations for one or more protein accessions.

## Implemented task

- `protein_accession_to_localization_annotation`
  - Input: one or more protein accessions from repeated `--accession`, text input, or CSV input
  - Output:
    - `uniprot_subcellular_annotation.tsv`
    - `summary.json`
    - optional `errors.json`
  - Behavior:
    - queries UniProtKB REST search for each accession
    - returns the best matching entry with the recorded `Subcellular location [CC]` text
    - does not download protein sequences

## Current boundary

This package only covers:

- `protein accession -> localization annotation`

This package does not cover:

- sequence download
- protein localization prediction
- cross-method consensus

## Notes

- Formal runs require `--protocol-check-file`.
- Batch accession input is treated as a delegated task under the current protocol.
