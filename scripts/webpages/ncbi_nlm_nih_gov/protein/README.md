# NCBI gene/protein preparation

Page and API entry points:

- `https://www.ncbi.nlm.nih.gov/`
- `https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/rest-api/`
- `https://www.ncbi.nlm.nih.gov/books/NBK25501/`

## Purpose

This package prepares one NCBI protein output folder for downstream protein analysis tasks.
It keeps the full protein view, the recommended protein view, and the recommended-protein FASTA in the same directory.

## Implemented task

- `gene_set_to_protein_bundle`
  - Input: one or more gene symbols from repeated `--gene`, text input, or CSV input
  - Output:
    - `query_genes.txt`
    - `matched_gene_summary.csv`
    - `all_proteins.csv`
    - `recommended_proteins.csv`
    - `recommended_protein_fasta_records.csv`
    - `recommended_proteins.fasta`
    - `summary.json`
    - optional `errors.json`
    - `temp/`
  - Behavior:
    - resolves all transcript/product records for each gene via NCBI Datasets `product_report`
    - keeps all protein-bearing products for each matched gene
    - ranks proteins and keeps one recommended protein per matched gene
    - fetches FASTA only for the recommended protein of each matched gene
    - preserves `gene_symbol <-> transcript_accession_version <-> protein_accession_version <-> fasta_header`

## Protein ranking rule

Recommended proteins are chosen by the following priority within the current NCBI-only boundary:

1. transcript select category: `MANE_SELECT`
2. transcript select category: `MANE_PLUS_CLINICAL`
3. transcript select category: `REFSEQ_SELECT`
4. protein accession priority: `NP_` > `XP_`
5. longer protein length
6. accession lexical order as a final tie-breaker

## Current boundary

This package only covers:

- `gene set -> recommended-protein sequence bundle`

This package does not cover:

- UniProtKB localization annotation
- CELLO prediction
- Cell-PLoc prediction
- any subcellular localization method
- cross-method localization consensus

## Output contract

Each formal run writes one NCBI protein bundle directory:

- `query_genes.txt`
- `matched_gene_summary.csv`
- `all_proteins.csv`
- `recommended_proteins.csv`
- `recommended_protein_fasta_records.csv`
- `recommended_proteins.fasta`
- `summary.json`
- optional `errors.json`
- `temp/`

`recommended_protein_fasta_records.csv` and `recommended_proteins.fasta` always correspond to the recommended protein set.

## Notes

- Formal runs require `--protocol-check-file`.
- This is the only user-facing NCBI protein task in this package.
- Batch gene input is treated as a delegated task under the current protocol.
