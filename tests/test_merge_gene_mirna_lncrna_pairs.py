from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "merge_gene_mirna_lncrna_pairs.py"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_merge_gene_mirna_lncrna_pairs(tmp_path: Path) -> None:
    pairs = tmp_path / "pairs.csv"
    lncbase = tmp_path / "lncbase.csv"
    encori = tmp_path / "encori.csv"
    output_dir = tmp_path / "out"

    write_csv(
        pairs,
        ["Gene", "miRNA", "n_db"],
        [
            {"Gene": "PIK3CA", "miRNA": "hsa-miR-19a-3p", "n_db": "3"},
            {"Gene": "VPS26A", "miRNA": "hsa-miR-370-3p", "n_db": "3"},
        ],
    )
    write_csv(
        lncbase,
        ["query_mirna", "result_mirna", "gene_name", "query_lncrna_count"],
        [
            {
                "query_mirna": "hsa-miR-19a-3p",
                "result_mirna": "hsa-miR-19a-3p",
                "gene_name": "KCNQ1OT1",
                "query_lncrna_count": "1",
            }
        ],
    )
    write_csv(
        encori,
        ["query_mirna", "miRNAname", "geneName", "query_lncrna_count"],
        [
            {
                "query_mirna": "hsa-miR-370-3p",
                "miRNAname": "hsa-miR-370-3p",
                "geneName": "DNM3OS",
                "query_lncrna_count": "1",
            }
        ],
    )

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pairs-csv",
            str(pairs),
            "--lncbase-csv",
            str(lncbase),
            "--encori-csv",
            str(encori),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    lncbase_out = output_dir / "gene_mirna_lncrna_pairs_lncbasev3.csv"
    encori_out = output_dir / "gene_mirna_lncrna_pairs_encori.csv"
    assert lncbase_out.exists()
    assert encori_out.exists()

    with lncbase_out.open("r", encoding="utf-8", newline="") as handle:
        lnc_rows = list(csv.DictReader(handle))
    with encori_out.open("r", encoding="utf-8", newline="") as handle:
        enc_rows = list(csv.DictReader(handle))

    assert len(lnc_rows) == 1
    assert lnc_rows[0]["Gene"] == "PIK3CA"
    assert lnc_rows[0]["lncbasev3_gene_name"] == "KCNQ1OT1"

    assert len(enc_rows) == 1
    assert enc_rows[0]["Gene"] == "VPS26A"
    assert enc_rows[0]["encori_geneName"] == "DNM3OS"
