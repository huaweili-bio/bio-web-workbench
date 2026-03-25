# bio-web-workbench

`bio-web-workbench` is a code-first repository for reproducible bioinformatics web workflows.

It packages small, composable task scripts for sequence preparation, localization analysis, RNA interaction discovery, and gene-set network export while keeping formal runs protocol-gated and auditable.

## Overview

Current public scope:

- RNA and protein subcellular localization workflows
- `mRNA -> miRNA` target discovery
- `miRNA -> lncRNA` target discovery
- `GeneMANIA` gene-set report export
- protocol-gated task execution

## Key Design Choices

- webpage tasks are organized per source under `scripts/webpages/`
- formal runs are fail-closed through `scripts/protocol_gate.py`
- generated outputs stay local and are not versioned by default
- public exports exclude caches, downloaded archives, and private workflow notes

## Repository Layout

- `data/`: small smoke-test example inputs only
- `docs/`: public quickstart and methods overview
- `scripts/protocol_gate.py`: fail-closed protocol gate used by formal tasks
- `scripts/merge_gene_mirna_lncrna_pairs.py`: helper for joining upstream `Gene-miRNA` pairs with downstream `miRNA-lncRNA` results
- `scripts/prepare_public_repo.py`: non-destructive public export builder
- `scripts/webpages/`: webpage-specific task packages, manifests, and task entrypoints

Generated outputs, caches, downloaded third-party archives, and local runtime directories are intentionally excluded.

This public-safe export also rewrites local absolute paths in documentation into repository-relative paths.

## What Is Not Included

The public export intentionally excludes:

- local task outputs and caches
- local `TargetScan` archives
- internal operator/agent workflow notes
- local-only command templates that rely on workstation-specific absolute paths in their original private form
- private working notes and temporary directories

Sanitized webpage `README.md` and `COMMANDS.md` files can be included in the exported public preview.

## Execution Model

Formal webpage tasks are designed to be fail-closed:

1. Identify the webpage package
2. Create a protocol check file with `scripts/protocol_gate.py`
3. Run the task script with `--protocol-check-file`

## Getting Started

- [Quickstart](docs/QUICKSTART.md)
- [Methods Overview](docs/METHODS.md)

## Public Snapshot Notes

- This public-safe snapshot is code-first. Some internal documentation is intentionally omitted because it contains local execution paths or private workflow conventions.
- Third-party websites and downloadable datasets may have their own usage terms. Public users should fetch external resources themselves when required.
- The repository license applies to this codebase only. External websites, models, and downloadable resources remain subject to their own terms.

## License

This repository is released under the [MIT License](LICENSE).
