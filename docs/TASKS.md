# Tasks

This public repository keeps only webpage runtime code and webpage tests. It does not include protocol gating, local results, caches, or private workflow files.

## Included webpages

### Sequence preparation

- `NCBI Gene`
  - Webpage: [NCBI Gene](https://www.ncbi.nlm.nih.gov/gene/)
  - Script: `scripts/webpages/ncbi_nlm_nih_gov/gene/tasks/gene_set_to_fasta_bundle.py`
  - Task: gene symbols to recommended transcript CSV and FASTA bundle
- `NCBI Protein`
  - Webpage: [NCBI Protein](https://www.ncbi.nlm.nih.gov/protein/)
  - Script: `scripts/webpages/ncbi_nlm_nih_gov/protein/tasks/gene_set_to_protein_bundle.py`
  - Task: gene symbols to recommended protein CSV and FASTA bundle

### RNA / protein localization

- `mRSLPred`
  - Webpage: [mRSLPred GitHub](https://github.com/raghavagps/mrslpred)
  - Script: `scripts/webpages/github_com/raghavagps_mrslpred/tasks/fasta_to_localization_bundle.py`
  - Task: transcript FASTA to RNA localization predictions plus PNG and PDF figure
- `RNALocate`
  - Webpage: [RNALocate](https://rnalocate.org/)
  - Script: `scripts/webpages/rnalocate_org/search/tasks/rna_symbol_to_localization_annotation.py`
  - Task: RNA symbols to localization annotations
- `UniProtKB`
  - Webpage: [UniProtKB](https://www.uniprot.org/uniprotkb)
  - Script: `scripts/webpages/uniprot_org/uniprotkb/tasks/protein_accession_to_localization_annotation.py`
  - Task: protein accessions to subcellular localization annotations
- `CELLO`
  - Webpage: [CELLO](https://cello.life.nctu.edu.tw/)
  - Script: `scripts/webpages/cello_life_nctu_edu_tw/root/tasks/protein_fasta_to_localization.py`
  - Task: protein or coding-sequence FASTA to protein localization predictions
- `Cell-PLoc 2.0`
  - Webpage: [Cell-PLoc 2.0](http://www.csbio.sjtu.edu.cn/bioinf/Cell-PLoc-2/)
  - Script: `scripts/webpages/csbio_sjtu_edu_cn/cell_ploc_2/tasks/human_protein_fasta_to_localization.py`
  - Task: human protein FASTA to protein localization predictions

### mRNA to miRNA

- `miRDB`
  - Webpage: [miRDB](https://mirdb.org/)
  - Script: `scripts/webpages/mirdb_org/index/tasks/mrna_to_mirna.py`
  - Task: gene symbols to mature miRNA predictions
- `ENCORI`
  - Webpage: [ENCORI](https://rnasysu.com/encori/)
  - Script: `scripts/webpages/rnasysu_com/encori/tasks/mrna_to_mirna.py`
  - Task: gene symbols to miRNA target interactions
- `TargetScanHuman 8.0`
  - Webpage: [TargetScanHuman 8.0](https://www.targetscan.org/vert_80/)
  - Script: `scripts/webpages/targetscan_org/vert_80/tasks/mrna_to_mirna.py`
  - Task: gene symbols to mature miRNA predicted targeting details

### miRNA to lncRNA

- `DIANA-LncBase v3`
  - Webpage: [DIANA-LncBase v3](https://diana.e-ce.uth.gr/lncbasev3/home)
  - Script: `scripts/webpages/diana_e_ce_uth_gr/lncbasev3_home/tasks/mirna_to_lncrna.py`
  - Task: miRNA to lncRNA targets
- `ENCORI`
  - Webpage: [ENCORI](https://rnasysu.com/encori/)
  - Script: `scripts/webpages/rnasysu_com/encori/tasks/mirna_to_lncrna.py`
  - Task: miRNA to lncRNA targets

### Gene set

- `GeneMANIA`
  - Webpage: [GeneMANIA](https://genemania.org/)
  - Script: `scripts/webpages/genemania_org/search/tasks/gene_set_to_report_figure.py`
  - Task: gene set to PDF and PNG network report

## Common runtime pattern

- Every task supports `--help`.
- Most tasks write final outputs into `--job-dir`.
- If `--job-dir` is omitted, the script creates a default directory under `outputs/tasks/`.
- Final user-facing outputs stay in the top level of `--job-dir`; debug files go into `temp/`.

Use this pattern to see full parameters:

```powershell
python scripts/webpages/mirdb_org/index/tasks/mrna_to_mirna.py --help
```

## Key parameters by task

### NCBI gene bundle

- Script: `scripts/webpages/ncbi_nlm_nih_gov/gene/tasks/gene_set_to_fasta_bundle.py`
- Main parameters:
  - `--gene`: one or more gene symbols
  - `--input`: text or CSV gene list
  - `--job-dir`: output directory
  - `--taxon`: organism, default `human`
  - `--timeout`: request timeout
- Example:

```powershell
python scripts/webpages/ncbi_nlm_nih_gov/gene/tasks/gene_set_to_fasta_bundle.py --gene PIK3CA --gene VPS26A --job-dir outputs/tasks/GeneSeq_NCBI_PIK3CA_VPS26A
```

### NCBI protein bundle

- Script: `scripts/webpages/ncbi_nlm_nih_gov/protein/tasks/gene_set_to_protein_bundle.py`
- Main parameters:
  - `--gene`
  - `--input`
  - `--job-dir`
  - `--taxon`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/ncbi_nlm_nih_gov/protein/tasks/gene_set_to_protein_bundle.py --gene PIK3CA --gene VPS26A --job-dir outputs/tasks/ProteinSeq_NCBI_PIK3CA_VPS26A
```

### mRSLPred

- Script: `scripts/webpages/github_com/raghavagps_mrslpred/tasks/fasta_to_localization_bundle.py`
- Main parameters:
  - `--input`: transcript FASTA
  - `--input-dir`: NCBI gene bundle directory
  - `--job-dir`
  - `--conda-env-name`: default `mrslpred_py37`
  - `--runtime-python`: use a specific Python instead of `conda run`
  - `--th1` to `--th6`: threshold overrides
- Example:

```powershell
python scripts/webpages/github_com/raghavagps_mrslpred/tasks/fasta_to_localization_bundle.py --input outputs/tasks/GeneSeq_NCBI_PIK3CA_VPS26A/recommended_transcripts.fasta --job-dir outputs/tasks/RNALoc_mRSLPred_PIK3CA_VPS26A
```

### RNALocate

- Script: `scripts/webpages/rnalocate_org/search/tasks/rna_symbol_to_localization_annotation.py`
- Main parameters:
  - `--rna`: one or more RNA symbols
  - `--input`
  - `--job-dir`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/rnalocate_org/search/tasks/rna_symbol_to_localization_annotation.py --rna PIK3CA --rna VPS26A --job-dir outputs/tasks/RNALoc_RNALocate_PIK3CA_VPS26A
```

### UniProtKB

- Script: `scripts/webpages/uniprot_org/uniprotkb/tasks/protein_accession_to_localization_annotation.py`
- Main parameters:
  - `--accession`: one or more protein accessions
  - `--input`: text or CSV accession file
  - `--job-dir`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/uniprot_org/uniprotkb/tasks/protein_accession_to_localization_annotation.py --accession P42336 --accession P05107 --job-dir outputs/tasks/ProteinLoc_UniProtKB_PIK3CA_ITGB2
```

### CELLO

- Script: `scripts/webpages/cello_life_nctu_edu_tw/root/tasks/protein_fasta_to_localization.py`
- Main parameters:
  - `--input`: FASTA file
  - `--job-dir`
  - `--seqtype`: `prot` or `dna`
  - `--species`: default `eu`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/cello_life_nctu_edu_tw/root/tasks/protein_fasta_to_localization.py --input outputs/tasks/ProteinSeq_NCBI_PIK3CA_VPS26A/recommended_proteins.fasta --job-dir outputs/tasks/ProteinLoc_CELLO_PIK3CA_VPS26A
```

### Cell-PLoc 2.0

- Script: `scripts/webpages/csbio_sjtu_edu_cn/cell_ploc_2/tasks/human_protein_fasta_to_localization.py`
- Main parameters:
  - `--input`: human protein FASTA
  - `--job-dir`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/csbio_sjtu_edu_cn/cell_ploc_2/tasks/human_protein_fasta_to_localization.py --input outputs/tasks/ProteinSeq_NCBI_PIK3CA_VPS26A/recommended_proteins.fasta --job-dir outputs/tasks/ProteinLoc_CellPLoc_PIK3CA_VPS26A
```

### miRDB

- Script: `scripts/webpages/mirdb_org/index/tasks/mrna_to_mirna.py`
- Main parameters:
  - `--gene`
  - `--input`
  - `--job-dir`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/mirdb_org/index/tasks/mrna_to_mirna.py --gene PIK3CA --gene VPS26A --job-dir outputs/tasks/mRNA_miRNA_miRDB_PIK3CA_VPS26A
```

### ENCORI mRNA to miRNA

- Script: `scripts/webpages/rnasysu_com/encori/tasks/mrna_to_mirna.py`
- Main parameters:
  - `--gene`
  - `--input`
  - `--job-dir`
  - `--assembly`
  - `--clip-exp-num`
  - `--degra-exp-num`
  - `--pancancer-num`
  - `--program-num`
  - `--program`
  - `--sleep-seconds`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/rnasysu_com/encori/tasks/mrna_to_mirna.py --gene PIK3CA --gene VPS26A --assembly hg38 --job-dir outputs/tasks/mRNA_miRNA_ENCORI_PIK3CA_VPS26A
```

### TargetScanHuman 8.0

- Script: `scripts/webpages/targetscan_org/vert_80/tasks/mrna_to_mirna.py`
- Main parameters:
  - `--gene`
  - `--input`
  - `--job-dir`
  - `--cache-dir`
  - `--local-mode`
  - `--local-data-dir`
- Example:

```powershell
python scripts/webpages/targetscan_org/vert_80/tasks/mrna_to_mirna.py --gene PIK3CA --gene VPS26A --local-mode --local-data-dir scripts/webpages/targetscan_org/vert_80/local_data --job-dir outputs/tasks/mRNA_miRNA_TargetScan_PIK3CA_VPS26A_local
```

Local mode expects these two manually downloaded files in `--local-data-dir`:

- `Conserved_Site_Context_Scores.txt.zip`
- `Nonconserved_Site_Context_Scores.txt.zip`

### DIANA-LncBase v3

- Script: `scripts/webpages/diana_e_ce_uth_gr/lncbasev3_home/tasks/mirna_to_lncrna.py`
- Main parameters:
  - `--mirna`
  - `--input`
  - `--job-dir`
  - `--species`
  - `--interaction-type`
  - `--tissue`
  - `--cell-type`
  - `--min-score`
  - `--sleep-seconds`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/diana_e_ce_uth_gr/lncbasev3_home/tasks/mirna_to_lncrna.py --mirna hsa-miR-19a-3p --mirna hsa-miR-145-5p --job-dir outputs/tasks/miRNA_lncRNA_LncBaseV3_miR19a_miR145
```

### ENCORI miRNA to lncRNA

- Script: `scripts/webpages/rnasysu_com/encori/tasks/mirna_to_lncrna.py`
- Main parameters:
  - `--mirna`
  - `--input`
  - `--job-dir`
  - `--assembly`
  - `--clip-exp-num`
  - `--degra-exp-num`
  - `--pancancer-num`
  - `--program-num`
  - `--program`
  - `--sleep-seconds`
  - `--timeout`
- Example:

```powershell
python scripts/webpages/rnasysu_com/encori/tasks/mirna_to_lncrna.py --mirna hsa-miR-19a-3p --mirna hsa-miR-145-5p --assembly hg38 --job-dir outputs/tasks/miRNA_lncRNA_ENCORI_miR19a_miR145
```

### GeneMANIA

- Script: `scripts/webpages/genemania_org/search/tasks/gene_set_to_report_figure.py`
- Main parameters:
  - `--gene`
  - `--job-dir`
  - `--organism-id`
  - `--top-functions`
  - `--layout`
  - `--browser`
  - `--png-dpi`
- Example:

```powershell
python scripts/webpages/genemania_org/search/tasks/gene_set_to_report_figure.py --gene PIK3CA --gene VPS26A --gene ITGB2 --job-dir outputs/tasks/GeneSetAnalysis_GeneMANIA_PIK3CA_VPS26A_ITGB2
```
