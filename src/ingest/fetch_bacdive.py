"""
BacDive (Bacterial Diversity) API integration.

BacDive is a comprehensive database of bacterial culturomics data including:
- Strain information and taxonomy
- Temperature/pH/oxygen preferences
- Carbon and nitrogen source utilization
- Media compositions and growth conditions
- Literature references

API: https://bacdive.dsmz.de/api/
Documentation: https://bacdive.dsmz.de/

Rate limiting: 3 requests per second (enforced by server)
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator

import requests

from src.config import DB_PATH, RAW_DIR

log = logging.getLogger(__name__)

BACDIVE_API = "https://bacdive.dsmz.de/api"
BACDIVE_DIR = RAW_DIR / "bacdive"
BACDIVE_CACHE = BACDIVE_DIR / "cache"

# Rate limiting: 1 request every 0.5 seconds (3 requests/second limit)
REQUEST_DELAY = 0.5

# BacDive taxonomy mapping to our organism types
BACDIVE_ORGANISM_TYPE_MAP = {
    "Bacteria": "bacteria",
    "Archaea": "archea",
    "Fungi": "fungi",
    "Eukaryota": "protist",
}


def init_bacdive_dirs() -> None:
    """Create BacDive data directories."""
    BACDIVE_DIR.mkdir(parents=True, exist_ok=True)
    BACDIVE_CACHE.mkdir(parents=True, exist_ok=True)
    log.info("Initialized BacDive directories: %s", BACDIVE_DIR)


def get_cache_path(strain_id: int) -> Path:
    """Get cache file path for BacDive strain."""
    return BACDIVE_CACHE / f"strain_{strain_id}.json"


def get_cached_strain(strain_id: int) -> dict[str, Any] | None:
    """Load strain data from cache if available."""
    cache_path = get_cache_path(strain_id)
    if cache_path.exists():
        with open(cache_path, "r") as f:
            return json.load(f)
    return None


def save_strain_cache(strain_id: int, data: dict[str, Any]) -> None:
    """Save strain data to cache."""
    cache_path = get_cache_path(strain_id)
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def search_bacdive(query: str, limit: int = 100) -> list[dict[str, Any]]:
    """
    Search BacDive for strains matching query.

    Args:
        query: Search query (species name, genus, phenotype, etc.)
        limit: Maximum results to return

    Returns:
        List of strain summaries with BacDive IDs
    """
    log.info("Searching BacDive: %s (limit=%d)", query, limit)

    url = f"{BACDIVE_API}/?search={query}"
    params = {"limit": limit}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        log.info("Found %d strains for query: %s", len(results), query)
        time.sleep(REQUEST_DELAY)

        return results

    except requests.RequestException as e:
        log.error("BacDive search failed for query '%s': %s", query, e)
        return []


def fetch_strain_details(strain_id: int | str) -> dict[str, Any] | None:
    """
    Fetch detailed strain information from BacDive.

    Args:
        strain_id: BacDive strain ID

    Returns:
        Detailed strain data or None if not found
    """
    # Check cache first
    cached = get_cached_strain(int(strain_id))
    if cached:
        log.debug("Using cached data for strain %s", strain_id)
        return cached

    log.debug("Fetching strain details: %s", strain_id)

    url = f"{BACDIVE_API}/{strain_id}/"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        save_strain_cache(int(strain_id), data)

        time.sleep(REQUEST_DELAY)
        return data

    except requests.RequestException as e:
        log.error("Failed to fetch strain %s: %s", strain_id, e)
        return None


def extract_growth_conditions(strain_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract culture conditions from BacDive strain data.

    BacDive stores this under different sections:
    - "Culture conditions": Temperature, pH, oxygen requirements
    - "Isolate": Original isolation conditions
    - "Physiology": Metabolic characteristics
    """
    conditions = {}

    # Temperature range
    if "Culture conditions" in strain_data:
        cult_cond = strain_data["Culture conditions"][0]
        if "temperature" in cult_cond:
            conditions["temperature"] = cult_cond["temperature"]
        if "pH" in cult_cond:
            conditions["pH"] = cult_cond["pH"]
        if "oxygen" in cult_cond:
            conditions["oxygen"] = cult_cond["oxygen"]

    # Carbon sources
    if "Physiology" in strain_data:
        phys = strain_data["Physiology"][0]
        if "Substrate utilization" in phys:
            conditions["carbon_sources"] = phys["Substrate utilization"]

    return conditions


def extract_media_preferences(strain_data: dict[str, Any]) -> list[str]:
    """
    Extract media types this strain grows in from BacDive data.

    Returns list of media names/types mentioned in the strain record.
    """
    media_list = []

    # Look in multiple fields for media information
    if "Culture conditions" in strain_data:
        for cult_cond in strain_data["Culture conditions"]:
            if "Medium" in cult_cond:
                media = cult_cond["Medium"]
                if isinstance(media, str):
                    media_list.append(media)
                elif isinstance(media, list):
                    media_list.extend(media)

    if "Physiology" in strain_data:
        for phys in strain_data["Physiology"]:
            if "Media used" in phys:
                media = phys["Media used"]
                if isinstance(media, str):
                    media_list.append(media)

    return list(set(media_list))


def ingest_bacdive_strain(
    strain_id: int | str,
    organism_type: str = "bacteria",
) -> dict[str, Any] | None:
    """
    Ingest a single strain from BacDive into the database.

    Args:
        strain_id: BacDive strain ID
        organism_type: Organism type (bacteria|archea|fungi|protist)

    Returns:
        Ingested strain data or None if failed
    """
    strain_data = fetch_strain_details(strain_id)
    if not strain_data:
        return None

    # Extract key information
    strain_name = strain_data.get("strain_name", f"Strain {strain_id}")
    species = strain_data.get("species", "Unknown")
    genus = strain_data.get("genus", "Unknown")

    # Try to get NCBI taxid
    taxid = None
    if "NCBI Taxonomy ID" in strain_data:
        try:
            taxid = int(strain_data["NCBI Taxonomy ID"])
        except (ValueError, TypeError):
            pass

    # Get culture conditions
    conditions = extract_growth_conditions(strain_data)

    log.info("Ingesting strain from BacDive: %s (%s %s)", strain_name, genus, species)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if strain already exists
        cursor.execute(
            "SELECT strain_id FROM strains WHERE species = ? AND strain_id = ?",
            (species, strain_id),
        )

        existing = cursor.fetchone()
        if existing:
            log.debug("Strain already in database: %s", strain_id)
            return strain_data

        # Insert strain
        cursor.execute(
            """
            INSERT INTO strains (strain_id, species, ccno, bacdive_id, domain)
            VALUES (?, ?, ?, ?, ?)
            """,
            (strain_id, species, strain_name, strain_id, organism_type[0].upper()),
        )

        # Extract and link growth conditions
        media_prefs = extract_media_preferences(strain_data)
        if media_prefs:
            log.debug("Found %d media preferences for strain %s", len(media_prefs), strain_id)

        conn.commit()
        log.info("Successfully ingested BacDive strain: %s", strain_id)
        return strain_data

    except sqlite3.Error as e:
        log.error("Failed to ingest BacDive strain: %s", e)
        return None

    finally:
        conn.close()


def search_and_ingest_bacdive(
    query: str,
    organism_type: str = "bacteria",
    limit: int = 50,
) -> int:
    """
    Search BacDive and ingest matching strains.

    Args:
        query: Search query
        organism_type: Organism type classification
        limit: Maximum strains to ingest

    Returns:
        Number of strains successfully ingested
    """
    log.info("Searching and ingesting BacDive: query=%s, organism_type=%s", query, organism_type)

    results = search_bacdive(query, limit=limit)
    ingested = 0

    for result in results:
        strain_id = result.get("id") or result.get("bacdive_id")
        if strain_id:
            if ingest_bacdive_strain(strain_id, organism_type=organism_type):
                ingested += 1

    log.info("Ingested %d/%d strains from BacDive", ingested, len(results))
    return ingested


def get_bacdive_statistics() -> dict[str, Any]:
    """Get statistics about BacDive data in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM strains WHERE bacdive_id IS NOT NULL")
        bacdive_strains = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT domain, COUNT(*) as count
            FROM strains
            WHERE bacdive_id IS NOT NULL
            GROUP BY domain
            """
        )
        by_domain = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_bacdive_strains": bacdive_strains,
            "by_domain": by_domain,
        }

    finally:
        conn.close()


def log_bacdive_ingest(
    task: str,
    status: str = "done",
    error_message: str | None = None,
) -> None:
    """Log BacDive ingestion task."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO ingest_log (task, status, error_message)
            VALUES (?, ?, ?)
            """,
            (f"bacdive_{task}", status, error_message),
        )
        conn.commit()

    finally:
        conn.close()
