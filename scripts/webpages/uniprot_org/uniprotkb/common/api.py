from __future__ import annotations

import csv
import io
from typing import Any
from urllib import parse, request


DEFAULT_API_DOC = "https://rest.uniprot.org/uniprotkb/search"
DEFAULT_FIELDS = [
    "accession",
    "id",
    "gene_names",
    "protein_name",
    "annotation_score",
    "reviewed",
    "cc_subcellular_location",
]
USER_AGENT = "bio-script-uniprot/1.0"
REFSEQ_PREFIXES = ("NP_", "XP_", "YP_", "WP_", "AP_", "ZP_")


class UniProtError(RuntimeError):
    """Raised when UniProtKB cannot be queried safely."""


class UniProtClient:
    def __init__(self, *, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def build_query_url(self, query: str, *, size: int = 1) -> str:
        params = {
            "query": query,
            "fields": ",".join(DEFAULT_FIELDS),
            "format": "tsv",
            "size": str(size),
        }
        return f"{DEFAULT_API_DOC}?{parse.urlencode(params)}"

    def _fetch_rows_for_query(self, query: str, *, size: int = 1) -> tuple[str, list[dict[str, str]]]:
        url = self.build_query_url(query, size=size)
        req = request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/tab-separated-values",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            raise UniProtError(f"Request failed for {url}: {exc}") from exc

        reader = csv.DictReader(io.StringIO(payload), delimiter="\t")
        rows = list(reader)
        return url, rows

    def _choose_best_row(self, rows: list[dict[str, str]]) -> list[dict[str, str]]:
        if not rows:
            return rows

        def score(row: dict[str, str]) -> tuple[int, float, int]:
            reviewed = 1 if row.get("Reviewed", "").strip().lower() == "reviewed" else 0
            annotation = row.get("Annotation", "").strip() or row.get("Annotation Score", "").strip() or "0"
            try:
                annotation_score = float(annotation.split()[0])
            except ValueError:
                annotation_score = 0.0
            has_location = 1 if row.get("Subcellular location [CC]", "").strip() else 0
            return (reviewed, annotation_score, has_location)

        return [max(rows, key=score)]

    def fetch_annotation_rows(
        self,
        accession: str,
        *,
        gene_symbol: str = "",
        organism_id: str = "",
    ) -> tuple[str, list[dict[str, str]]]:
        last_error: Exception | None = None
        queries: list[tuple[str, int]] = []
        normalized_accession = accession.strip()
        looks_like_refseq = normalized_accession.upper().startswith(REFSEQ_PREFIXES)
        if gene_symbol:
            if organism_id:
                queries.append((f"reviewed:true AND gene_exact:{gene_symbol} AND organism_id:{organism_id}", 5))
                queries.append((f"gene_exact:{gene_symbol} AND organism_id:{organism_id}", 5))
            queries.append((f"reviewed:true AND gene:{gene_symbol}", 5))
            queries.append((f"gene:{gene_symbol}", 5))
        if normalized_accession and not looks_like_refseq:
            queries.append((f"accession:{normalized_accession}", 1))
        elif normalized_accession:
            queries.append((f"accession:{normalized_accession}", 1))

        for query, size in queries:
            try:
                url, rows = self._fetch_rows_for_query(query, size=size)
            except UniProtError as exc:
                last_error = exc
                continue
            if rows:
                return url, self._choose_best_row(rows)
        if last_error is not None:
            raise last_error
        if not queries:
            return self._fetch_rows_for_query(f"accession:{normalized_accession}")
        url, rows = self._fetch_rows_for_query(queries[0][0], size=queries[0][1])
        return url, self._choose_best_row(rows)


def build_annotation_row(*, query_accession: str, source_url: str, payload_row: dict[str, str]) -> dict[str, Any]:
    return {
        "query_accession": query_accession,
        "entry": payload_row.get("Entry", "").strip(),
        "entry_name": payload_row.get("Entry Name", "").strip(),
        "gene_names": payload_row.get("Gene Names", "").strip(),
        "protein_name": payload_row.get("Protein names", "").strip(),
        "annotation_score": payload_row.get("Annotation", "").strip() or payload_row.get("Annotation Score", "").strip(),
        "reviewed": payload_row.get("Reviewed", "").strip(),
        "subcellular_location_text": payload_row.get("Subcellular location [CC]", "").strip(),
        "source_url": source_url,
    }
