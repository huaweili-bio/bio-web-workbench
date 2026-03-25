# bio-web-workbench

`bio-web-workbench` is a lightweight bioinformatics workflow repository focused on reproducible web-task automation.

Current public-safe scope:

- RNA and protein subcellular localization workflows
- `mRNA -> miRNA` target discovery
- `miRNA -> lncRNA` target discovery
- `GeneMANIA` gene-set report export
- protocol-gated task execution

## Public Repository Layout

- `data/`: small smoke-test example inputs only
- `scripts/protocol_gate.py`: fail-closed protocol gate used by formal tasks
- `scripts/merge_gene_mirna_lncrna_pairs.py`: helper for joining upstream `Gene-miRNA` pairs with downstream `miRNA-lncRNA` results
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

## Notes

- This public-safe snapshot is code-first. Some internal documentation is intentionally omitted because it contains local execution paths or private workflow conventions.
- Third-party websites and downloadable datasets may have their own usage terms. Public users should fetch external resources themselves when required.

Additional public-facing docs:

- [Quickstart](docs/QUICKSTART.md)
- [Methods Overview](docs/METHODS.md)
