# RNALocate RNA localization annotation

Page entry points:

- `https://www.rnalocate.org/`
- `http://www.rnalocate.org/show_search`

## Purpose

This package fetches existing RNALocate subcellular localization annotations for one or more RNA symbols.

## Implemented task

- `rna_symbol_to_localization_annotation`
  - Input: one or more RNA symbols from repeated `--rna`, text input, or CSV input
  - Output:
    - `rnalocate_localization_annotation.tsv`
    - `raw_response.html`
    - `summary.json`
    - optional `errors.json`
  - Behavior:
    - queries the RNALocate `show_search` endpoint with exact symbol search
    - parses the returned result table into a stable TSV
    - stores the raw HTML for traceability

## Current boundary

This package only covers:

- `RNA symbol -> localization annotation`

This package does not cover:

- RNALocate RNA-seq analysis
- RNALocate prediction modules
- cross-method consensus

## Notes

- Formal runs require `--protocol-check-file`.
- Batch symbol input is treated as a delegated task under the current protocol.
