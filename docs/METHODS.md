# Methods Overview

This is a public-facing summary of the currently implemented workflow areas.

## RNA / Protein Localization

- RNA localization:
  - `mRSLPred`
  - `RNALocate`
- Protein localization:
  - `UniProtKB`
  - `CELLO`
  - `Cell-PLoc 2.0`
- Sequence preparation:
  - `NCBI gene`
  - `NCBI protein`

## mRNA -> miRNA

- `miRDB`
- `ENCORI`
- `TargetScanHuman 8.0`

## miRNA -> lncRNA

- `DIANA-LncBase v3`
- `ENCORI`

## Gene Set Analysis

- `GeneMANIA`

## Output Philosophy

- Final result directories keep only user-facing files at the top level
- Intermediate files, summaries, raw responses, and protocol records are stored under `temp/`
- Formal tasks are designed to fail closed when protocol checks are missing
