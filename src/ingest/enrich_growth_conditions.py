"""
Growth condition and media enrichment module.

Links organisms to culture media and growth conditions by:
1. Parsing scientific literature (PubMed abstracts)
2. Querying growth databases
3. Inferring from organism phenotype/metabolism
4. Manual curated datasets

This enables CVAE training on organism-media-growth triplets.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

import requests

from src.config import DB_PATH

log = logging.getLogger(__name__)

# Literature search for culture conditions
PUBMED_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Growth database resources
GROWTHCOND_DATABASES = {
    "optimal_temps": {
        "mesophile": (20, 45),
        "thermophile": (45, 122),
        "psychrophile": (-10, 15),
        "halophile": (10, 50),  # Salt-loving, any temp
    },
    "optimal_ph": {
        "neutrophile": (6.0, 8.0),
        "acidophile": (1.0, 5.0),
        "alkaliphile": (8.0, 14.0),
    },
    "oxygen_requirements": {
        "aerobic": "requires",
        "anaerobic": "none",
        "facultative": "optional",
        "microaerophilic": "low",
    },
}


def infer_growth_conditions_from_taxonomy(
    organism_name: str,
    organism_type: str,
) -> dict[str, Any]:
    """
    Infer likely growth conditions from organism name/type.

    Examples:
    - "Thermoplasma acidophilum" → thermophile, acidophile
    - "Halobacterium salinarum" → halophile, aerobic
    - "Clostridium botulinum" → anaerobic
    """
    conditions = {
        "organism_name": organism_name,
        "organism_type": organism_type,
        "inferred_from": "taxonomy",
        "confidence": 0.3,
    }

    organism_lower = organism_name.lower()

    # Temperature preferences
    if any(term in organism_lower for term in ["thermophil", "thermal", "hot"]):
        conditions["temperature_preference"] = "thermophile"
        conditions["temperature_range_c"] = [45, 122]
    elif any(term in organism_lower for term in ["psychro", "cold", "cryo"]):
        conditions["temperature_preference"] = "psychrophile"
        conditions["temperature_range_c"] = [-10, 15]
    else:
        conditions["temperature_preference"] = "mesophile"
        conditions["temperature_range_c"] = [20, 45]

    # pH preferences
    if any(term in organism_lower for term in ["acidophil", "acidic", "acidobacter"]):
        conditions["pH_preference"] = "acidophile"
        conditions["pH_range"] = [1.0, 5.0]
    elif any(term in organism_lower for term in ["alkaliphil", "alkaline"]):
        conditions["pH_preference"] = "alkaliphile"
        conditions["pH_range"] = [8.0, 14.0]
    else:
        conditions["pH_preference"] = "neutrophile"
        conditions["pH_range"] = [6.0, 8.0]

    # Salt tolerance
    if any(term in organism_lower for term in ["haloba", "halococ", "halophil", "salt"]):
        conditions["salt_preference"] = "halophile"
        conditions["salt_concentration_m"] = [0.5, 5.0]

    # Oxygen requirements
    if any(term in organism_lower for term in ["clostr", "anaerob"]):
        conditions["oxygen_requirement"] = "anaerobic"
    elif any(term in organism_lower for term in ["aerob"]):
        conditions["oxygen_requirement"] = "aerobic"
    else:
        conditions["oxygen_requirement"] = "facultative"

    return conditions


def search_pubmed_growth_conditions(
    organism_name: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search PubMed for literature on organism growth conditions.

    Args:
        organism_name: Organism name to search
        limit: Max abstracts to retrieve

    Returns:
        List of relevant abstracts with metadata
    """
    log.info("Searching PubMed for growth conditions: %s", organism_name)

    query = f'"{organism_name}" AND ("culture condition" OR "growth medium" OR "media" OR "cultivation")'

    url = f"{PUBMED_EUTILS}/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "rettype": "json",
        "tool": "mediadive_cvae",
        "email": "research@mediadive.local",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])

        log.info("Found %d PubMed articles for: %s", len(pmids), organism_name)

        # Fetch summaries
        results = []
        for pmid in pmids[:limit]:
            summary = fetch_pubmed_summary(pmid)
            if summary:
                results.append(summary)

        return results

    except Exception as e:
        log.error("PubMed search failed for %s: %s", organism_name, e)
        return []


def fetch_pubmed_summary(pmid: str) -> dict[str, Any] | None:
    """Fetch PubMed abstract summary."""
    try:
        url = f"{PUBMED_EUTILS}/esummary.fcgi"
        params = {
            "db": "pubmed",
            "id": pmid,
            "rettype": "json",
            "tool": "mediadive_cvae",
            "email": "research@mediadive.local",
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        result = data.get("result", {}).get(pmid, {})

        return {
            "pmid": pmid,
            "title": result.get("title", ""),
            "abstract": result.get("abstract", ""),
            "pubdate": result.get("pubdate", ""),
        }

    except Exception as e:
        log.error("Failed to fetch PubMed summary for %s: %s", pmid, e)
        return None


def extract_growth_params_from_abstract(abstract: str) -> dict[str, Any]:
    """
    Parse abstract text for growth parameters (simple heuristic).

    Looks for: pH ranges, temperatures, media names, carbon sources, etc.
    """
    params = {}

    abstract_lower = abstract.lower()

    # Temperature
    import re

    temp_pattern = r"(\d+)\s*(?:°c|celsius|c\b)"
    temps = re.findall(temp_pattern, abstract_lower)
    if temps:
        params["temperatures_found"] = [int(t) for t in temps]

    # pH
    ph_pattern = r"ph\s*(?:=|:)?\s*(\d\.?\d*)"
    phs = re.findall(ph_pattern, abstract_lower)
    if phs:
        params["pH_values_found"] = [float(p) for p in phs]

    # Media names
    media_names = ["lB", "YPD", "M9", "TSB", "rich medium", "minimal medium"]
    found_media = [m for m in media_names if m.lower() in abstract_lower]
    if found_media:
        params["media_mentioned"] = found_media

    # Carbon sources
    carbon_sources = ["glucose", "acetate", "succinate", "pyruvate", "glycerol", "lactose"]
    found_carbons = [c for c in carbon_sources if c.lower() in abstract_lower]
    if found_carbons:
        params["carbon_sources_mentioned"] = found_carbons

    return params


def link_organism_to_media(
    organism_name: str,
    media_id: str,
    growth: bool = True,
    confidence: float = 0.5,
    source: str = "inferred",
) -> bool:
    """
    Link organism to a media in genome_growth table.

    Args:
        organism_name: Organism name
        media_id: MediaDive media ID
        growth: Whether organism grows in this media
        confidence: Confidence score [0-1]
        source: Data source (literature, inferred, experimental, curated)

    Returns:
        True if successful
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Find genome by organism name
        cursor.execute(
            'SELECT genome_id FROM genomes WHERE organism_name LIKE ?',
            (f"%{organism_name}%",),
        )

        result = cursor.fetchone()
        if not result:
            log.warning("Organism not found in database: %s", organism_name)
            return False

        genome_id = result[0]

        # Insert or update growth observation
        cursor.execute(
            """
            INSERT OR REPLACE INTO genome_growth
            (genome_id, media_id, growth, confidence, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (genome_id, media_id, int(growth), confidence, source),
        )

        conn.commit()
        log.debug("Linked organism to media: %s → %s", organism_name, media_id)
        return True

    except sqlite3.Error as e:
        log.error("Failed to link organism to media: %s", e)
        return False

    finally:
        conn.close()


def enrich_organism_conditions(organism_name: str) -> dict[str, Any]:
    """
    Comprehensively enrich organism with growth conditions.

    Combines:
    1. Taxonomic inference
    2. Literature search
    3. Database lookups

    Returns:
        Enriched condition data
    """
    log.info("Enriching growth conditions for: %s", organism_name)

    conditions = {}

    # 1. Infer from taxonomy
    tax_conditions = infer_growth_conditions_from_taxonomy(organism_name, "bacteria")
    conditions["inferred"] = tax_conditions

    # 2. Search literature
    pubmed_results = search_pubmed_growth_conditions(organism_name, limit=5)
    if pubmed_results:
        conditions["literature"] = {
            "articles_found": len(pubmed_results),
            "abstracts": pubmed_results,
            "extracted_params": [extract_growth_params_from_abstract(r.get("abstract", "")) for r in pubmed_results],
        }

    # Overall confidence is average of components
    if "literature" in conditions and conditions["literature"].get("articles_found", 0) > 0:
        conditions["overall_confidence"] = 0.7  # High if literature found
    else:
        conditions["overall_confidence"] = 0.3  # Low if only inference

    return conditions


def get_enrichment_statistics() -> dict[str, Any]:
    """Get statistics on growth condition enrichment."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Count genome-media links by source
        cursor.execute(
            """
            SELECT source, COUNT(*) as count
            FROM genome_growth
            GROUP BY source
            """
        )

        return {row[0]: row[1] for row in cursor.fetchall()}

    finally:
        conn.close()


def create_curated_growth_map() -> dict[str, list[tuple[str, float]]]:
    """
    Curated mapping of organism patterns to media.

    Returns dict mapping organism_pattern → [(media_id, confidence), ...]
    """
    return {
        # Bacteria (common lab strains)
        "Escherichia coli": [("48", 0.95), ("1", 0.9), ("2", 0.85)],  # LB, nutrient, glucose
        "Bacillus subtilis": [("48", 0.9), ("1", 0.85), ("3", 0.8)],
        "Streptococcus": [("5", 0.85), ("6", 0.8)],  # Blood agar derivatives
        "Staphylococcus": [("5", 0.9), ("6", 0.85)],
        # Thermophiles
        "Thermus": [("10", 0.8), ("11", 0.75)],  # High-temp media
        "Thermoproteus": [("10", 0.8)],
        # Halophiles
        "Halobacterium": [("20", 0.85)],  # Salt media
        "Halomonas": [("20", 0.8), ("21", 0.75)],
        # Acidophiles
        "Acidobacteria": [("30", 0.8)],  # Acidic media
        "Thiobacillus": [("30", 0.85)],
        # Fungi
        "Saccharomyces": [("50", 0.9), ("51", 0.85)],  # YPD, rich media
        "Aspergillus": [("52", 0.85), ("53", 0.8)],
        "Candida": [("51", 0.9)],
        # Protists
        "Tetrahymena": [("60", 0.8)],  # Ciliate media
        "Paramecium": [("61", 0.75)],
    }
