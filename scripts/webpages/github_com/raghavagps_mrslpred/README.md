# mRSLPred GitHub runtime

Page and source entry points:

- `https://github.com/raghavagps/mrslpred`
- `https://webs.iiitd.edu.in/raghava/mrslpred/`

## Purpose

This package wraps the standalone GitHub version of `mRSLPred` for local execution.
It exists because the public web server is often unreachable, while the GitHub runtime can still be reproduced locally.

## Implemented task

- `fasta_to_localization_bundle`
  - Input: a FASTA file or an NCBI bundle directory containing `recommended_transcripts.fasta`
  - Output:
    - `mrslpred_result.csv`
    - `mrslpred_localization_figure.png`
    - `mrslpred_localization_figure.pdf`
    - `summary.json`
    - optional `errors.json`
    - `temp/`
  - Behavior:
    - runs the official standalone runtime
    - writes the merged repo-style prediction result
    - renders the localization figure with transcript labels
    - exports both `PNG` and `PDF`

## Runtime requirement

The current main repository Python is not suitable for the official model pickle.
Use a dedicated conda environment such as:

```powershell
conda create -y -n mrslpred_py37 python=3.7 numpy pandas biopython scikit-learn=1.0.2 py-xgboost=0.90
```

The task script defaults to `conda run -n mrslpred_py37 python ...`.
If you want to use another compatible interpreter, pass `--runtime-python`.

## Current boundary

This package only covers:

- `FASTA -> prediction result + figure bundle`

This package does not cover:

- transcript discovery
- transcript FASTA download
- plotting or enrichment analysis after localization prediction

## Output contract

Each formal run writes one mRSLPred bundle directory containing:

- `mrslpred_result.csv`
- `mrslpred_localization_figure.png`
- `mrslpred_localization_figure.pdf`
- `summary.json`
- optional `errors.json`
- `temp/`

The official raw outputs remain inside `temp/official_output/` for debugging and traceability.

## Notes

- Formal runs require `--protocol-check-file`.
- Batch FASTA input is treated as a delegated task under the current protocol.
- This is now the only user-facing mRSLPred task in this package.
