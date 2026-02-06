"""
NCBI Entrez utilities integration for fungi and protist genomic data.

Fetches organism metadata, taxonomy, and genome sequences from:
- NCBI GenBank (genomes)
- NCBI Taxonomy Database
- NCBI Nucleotide Database

Supports: Fungi, Protists, and other eukaryotic microbes

NCBI E-utilities: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25497/

Rate limiting: 3 requests/second (10 with API key)
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

import requests

from src.config import DB_PATH, RAW_DIR

log = logging.getLogger(__name__)

NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_DIR = RAW_DIR / "ncbi"
NCBI_GENOMES_DIR = NCBI_DIR / "genomes"
NCBI_CACHE = NCBI_DIR / "cache"

# NCBI E-utilities registration
# Users should set these in .env to get higher rate limits
TOOL = "mediadive_cvae"
EMAIL = "research@mediadive.local"
API_KEY = None  # Set from environment if available

# Rate limiting: 1 request per 0.5 seconds (3/sec limit)
REQUEST_DELAY = 0.5


def init_ncbi_dirs() -> None:
    """Create NCBI data directories."""
    NCBI_GENOMES_DIR.mkdir(parents=True, exist_ok=True)
    NCBI_CACHE.mkdir(parents=True, exist_ok=True)
    log.info("Initialized NCBI directories: %s", NCBI_DIR)


def build_ncbi_url(endpoint: str, **params: Any) -> str:
    """
    Build NCBI E-utility URL with parameters.

    Args:
        endpoint: E-utility endpoint (esearch, esummary, efetch, etc.)
        **params: Query parameters

    Returns:
        Full URL with parameters
    """
    base = f"{NCBI_EUTILS}/{endpoint}.fcgi"

    # Add registration parameters
    params["tool"] = TOOL
    params["email"] = EMAIL
    if API_KEY:
        params["api_key"] = API_KEY

    # Build query string
    query_parts = []
    for key, value in params.items():
        if value is not None:
            encoded_value = quote(str(value)) if isinstance(value, str) else str(value)
            query_parts.append(f"{key}={encoded_value}")

    return base + "?" + "&".join(query_parts)


def ncbi_search(
    database: str,
    query: str,
    max_results: int = 100,
) -> list[str] | None:
    """
    Search NCBI using ESearch.

    Args:
        database: NCBI database (nuccore, protein, assembly, taxonomy, etc.)
        query: Search query string
        max_results: Maximum results to return

    Returns:
        List of UIDs (unique identifiers) or None if failed
    """
    log.debug("NCBI search: db=%s, query=%s", database, query)

    url = build_ncbi_url(
        "esearch",
        db=database,
        term=query,
        retmax=min(max_results, 1000),
        rettype="json",
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        uids = data.get("esearchresult", {}).get("idlist", [])

        log.debug("Found %d results", len(uids))
        time.sleep(REQUEST_DELAY)

        return uids

    except Exception as e:
        log.error("NCBI search failed: %s", e)
        return None


def ncbi_fetch_summary(
    database: str,
    uids: list[str],
) -> dict[str, Any] | None:
    """
    Get document summaries for UIDs using ESummary.

    Args:
        database: NCBI database
        uids: List of UIDs

    Returns:
        Summaries data or None if failed
    """
    if not uids:
        return None

    uid_str = ",".join(uids[:100])  # Max 100 per request
    log.debug("ESummary: fetching %d records from %s", len(uids), database)

    url = build_ncbi_url(
        "esummary",
        db=database,
        id=uid_str,
        rettype="json",
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        time.sleep(REQUEST_DELAY)

        return data.get("result", {})

    except Exception as e:
        log.error("NCBI esummary failed: %s", e)
        return None


def search_fungal_genomes(genus: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """
    Search for fungal genome assemblies in NCBI.

    Args:
        genus: Filter by genus (e.g., "Saccharomyces", "Aspergillus")
        limit: Maximum results

    Returns:
        List of genome metadata
    """
    # Build query for fungi genomes
    if genus:
        query = f'"{genus}"[Organism] AND (fungi[Organism] OR fungal[All Fields])'
    else:
        query = "fungi[Organism] OR fungal[All Fields]"

    query += " AND complete genome"

    log.info("Searching for fungal genomes: %s (limit=%d)", genus or "all fungi", limit)

    uids = ncbi_search("assembly", query, max_results=limit)
    if not uids:
        return []

    summaries = ncbi_fetch_summary("assembly", uids)
    if not summaries:
        return []

    genomes = []
    for uid in uids:
        if uid in summaries:
            summary = summaries[uid]
            genome_info = {
                "ncbi_uid": uid,
                "organism_name": summary.get("taxid", ""),
                "accession": summary.get("accessiontype", ""),
                "taxid": summary.get("taxid", ""),
            }
            genomes.append(genome_info)

    return genomes[:limit]


def search_protist_genomes(limit: int = 50) -> list[dict[str, Any]]:
    """
    Search for protist genome assemblies in NCBI.

    Args:
        limit: Maximum results

    Returns:
        List of genome metadata
    """
    # Protists are eukaryotic but not fungi/animals/plants
    query = "(protist[Organism] OR protozoa[Organism]) AND complete genome"

    log.info("Searching for protist genomes (limit=%d)", limit)

    uids = ncbi_search("assembly", query, max_results=limit)
    if not uids:
        return []

    summaries = ncbi_fetch_summary("assembly", uids)
    if not summaries:
        return []

    genomes = []
    for uid in uids:
        if uid in summaries:
            summary = summaries[uid]
            genome_info = {
                "ncbi_uid": uid,
                "organism_name": summary.get("organism_name", ""),
                "accession": summary.get("accessiontype", ""),
                "taxid": summary.get("taxid", ""),
            }
            genomes.append(genome_info)

    return genomes[:limit]


def fetch_ncbi_taxonomy(taxid: int) -> dict[str, Any] | None:
    """
    Fetch taxonomy information from NCBI.

    Args:
        taxid: NCBI taxonomy ID

    Returns:
        Taxonomy data
    """
    log.debug("Fetching taxonomy for taxid: %s", taxid)

    uids = ncbi_search("taxonomy", f"{taxid}[UID]", max_results=1)
    if not uids:
        return None

    summary = ncbi_fetch_summary("taxonomy", uids)
    return summary.get(uids[0]) if summary else None


def store_ncbi_organism(
    ncbi_uid: str,
    organism_name: str,
    organism_type: str,
    taxid: int | None = None,
    accession: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Store NCBI organism in database.

    Args:
        ncbi_uid: NCBI unique identifier
        organism_name: Full organism name
        organism_type: One of (bacteria, fungi, protist, virus)
        taxid: NCBI taxonomy ID
        accession: GenBank/RefSeq accession
        metadata: Additional metadata

    Returns:
        True if successful
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if already exists
        cursor.execute(
            "SELECT genome_id FROM genomes WHERE organism_name = ? AND organism_type = ?",
            (organism_name, organism_type),
        )

        if cursor.fetchone():
            log.debug("Organism already in database: %s", organism_name)
            return True

        # Insert as genome record
        fasta_path = f"{organism_type}/{accession or ncbi_uid}.fasta"

        cursor.execute(
            """
            INSERT INTO genomes (
                genome_id, organism_name, organism_type, taxid, fasta_path
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (ncbi_uid, organism_name, organism_type, taxid, fasta_path),
        )

        # Store metadata
        if metadata:
            meta_path = NCBI_CACHE / f"{ncbi_uid}_metadata.json"
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

        conn.commit()
        log.info("Stored NCBI organism: %s (%s)", organism_name, organism_type)
        return True

    except sqlite3.Error as e:
        log.error("Failed to store NCBI organism: %s", e)
        return False

    finally:
        conn.close()


def ingest_fungal_species(genus: str | None = None, limit: int = 50) -> int:
    """
    Search and ingest fungal genome metadata from NCBI.

    Args:
        genus: Filter by genus
        limit: Max genomes to ingest

    Returns:
        Number ingested
    """
    log.info("Ingesting fungal genomes from NCBI (genus=%s)", genus or "all")

    genomes = search_fungal_genomes(genus=genus, limit=limit)
    ingested = 0

    for genome in genomes:
        if store_ncbi_organism(
            ncbi_uid=genome["ncbi_uid"],
            organism_name=genome.get("organism_name", "Unknown"),
            organism_type="fungi",
            taxid=genome.get("taxid"),
            accession=genome.get("accession"),
            metadata=genome,
        ):
            ingested += 1

    log.info("Ingested %d fungal genomes", ingested)
    return ingested


def ingest_protist_species(limit: int = 50) -> int:
    """
    Search and ingest protist genome metadata from NCBI.

    Args:
        limit: Max genomes to ingest

    Returns:
        Number ingested
    """
    log.info("Ingesting protist genomes from NCBI")

    genomes = search_protist_genomes(limit=limit)
    ingested = 0

    for genome in genomes:
        if store_ncbi_organism(
            ncbi_uid=genome["ncbi_uid"],
            organism_name=genome.get("organism_name", "Unknown"),
            organism_type="protist",
            taxid=genome.get("taxid"),
            accession=genome.get("accession"),
            metadata=genome,
        ):
            ingested += 1

    log.info("Ingested %d protist genomes", ingested)
    return ingested


def get_ncbi_statistics() -> dict[str, Any]:
    """Get statistics about NCBI data in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT organism_type, COUNT(*) as count
            FROM genomes
            WHERE fasta_path LIKE 'ncbi/%' OR fasta_path LIKE 'fungi/%' OR fasta_path LIKE 'protist/%'
            GROUP BY organism_type
            """
        )

        return {row[0]: row[1] for row in cursor.fetchall()}

    finally:
        conn.close()


def log_ncbi_ingest(
    task: str,
    status: str = "done",
    error_message: str | None = None,
) -> None:
    """Log NCBI ingestion task."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO ingest_log (task, status, error_message)
            VALUES (?, ?, ?)
            """,
            (f"ncbi_{task}", status, error_message),
        )
        conn.commit()

    finally:
        conn.close()
