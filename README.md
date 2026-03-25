# bio-web-workbench

`bio-web-workbench` is a public-facing code snapshot for running webpage-specific bioinformatics tasks locally.

This public repository keeps only:

- webpage runtime code under `scripts/webpages/`
- webpage-oriented tests under `tests/`
- minimal public docs and installation notes

This public snapshot does not include protocol gating, local outputs, caches, private notes, or downloaded third-party archives.

## Included workflows

- sequence preparation from `NCBI Gene` and `NCBI Protein`
- RNA and protein localization from `mRSLPred`, `RNALocate`, `UniProtKB`, `CELLO`, and `Cell-PLoc 2.0`
- `mRNA -> miRNA` from `miRDB`, `ENCORI`, and `TargetScanHuman 8.0`
- `miRNA -> lncRNA` from `DIANA-LncBase v3` and `ENCORI`
- gene-set report export from `GeneMANIA`

## Install

Create a clean environment and install the public requirements:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Notes:

- `GeneMANIA` requires the `playwright` Python package plus a local Chromium install.
- `mRSLPred` uses the upstream standalone runtime. By default the wrapper expects `conda run -n mrslpred_py37 python ...`. You can also point it at a specific interpreter with `--runtime-python`.
- `TargetScanHuman 8.0` local mode needs two large score archives that are not redistributed here. See [docs/TASKS.md](docs/TASKS.md).

## How to run

Every task is a normal Python script. Public usage no longer requires a protocol ticket.

Examples:

```powershell
python scripts/webpages/mirdb_org/index/tasks/mrna_to_mirna.py --gene PIK3CA --job-dir outputs/tasks/mRNA_miRNA_miRDB_PIK3CA
python scripts/webpages/rnalocate_org/search/tasks/rna_symbol_to_localization_annotation.py --rna PIK3CA --job-dir outputs/tasks/RNALoc_RNALocate_PIK3CA
python scripts/webpages/genemania_org/search/tasks/gene_set_to_report_figure.py --gene PIK3CA --gene VPS26A --job-dir outputs/tasks/GeneSetAnalysis_GeneMANIA_PIK3CA_VPS26A
```

For the full task list, key parameters, and example commands, see [docs/TASKS.md](docs/TASKS.md).

## Repository layout

- `scripts/webpages/`: webpage runtime code only
- `tests/`: public webpage tests only
- `docs/TASKS.md`: task list, webpages, parameters, and example commands
- `requirements.txt`: Python packages needed for local execution

## Testing

Run the public test suite with:

```powershell
pytest -q tests
```

## License

This code is released under the [MIT License](LICENSE).
