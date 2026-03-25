# Public Repo Scope

This document defines the first-round public sanitization boundary for `bio-web-workbench`.

## Included In The Public Export

- root `.gitignore`
- root `LICENSE`
- public-facing root `README.md`
- small smoke inputs under `data/`
- public-facing docs under `docs/`
- task code under `scripts/webpages/`
- selected helper scripts:
  - `scripts/protocol_gate.py`
  - `scripts/merge_gene_mirna_lncrna_pairs.py`
  - `scripts/prepare_public_repo.py`

## Excluded In The Public Export

- `outputs/`
- `temp/`
- benchmark and pytest temp directories
- local third-party archives under `scripts/webpages/targetscan_org/vert_80/local_data/`
- internal operator documents:
  - `scripts/EXECUTION_PROTOCOL.md`
  - `scripts/AGENT_BRIEF.md`
  - `scripts/START_HERE.md`
  - `scripts/TASK_INDEX.md`
- private working notes and temporary directories

## First-Round Goal

The first round is intentionally non-destructive:

- do not delete existing local files
- do not remove private workflow files from the working repository
- instead, generate a sanitized export preview in a separate directory

## Second-Round Goal

- include webpage `README.md` and `COMMANDS.md` in the public preview after rewriting local absolute paths to repository-relative paths
- make tests path-agnostic so they can be included in the public preview
- still keep the private working repository intact

## Later Rounds

Future public-cleanup rounds should:

1. rewrite webpage docs to use relative paths
2. make tests path-agnostic
3. replace personal commit email with GitHub noreply identity for public history
4. review third-party licensing and redistribution boundaries
