"""
Genome ingestion module.

Fetches and stores microbial genomes (FASTA) from public databases:
- NCBI RefSeq
- NCBI GenBank
- MGnify
- IMG/M

Supports bacteria, archea, fungi, protists, and other microbes.
Tracks organism type for curriculum learning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.config import DB_PATH, RAW_DIR

log = logging.getLogger(__name__)

GENOMES_DIR = RAW_DIR / "genomes"
GENOMES_METADATA_DIR = RAW_DIR / "genomes_metadata"

# Map organism types to common characteristics
ORGANISM_TYPES = {
    "bacteria": {"suffix": "bacteria", "priority": 1},  # Train first
    "archea": {"suffix": "archea", "priority": 2},
    "fungi": {"suffix": "fungi", "priority": 3},
    "protist": {"suffix": "protist", "priority": 4},
    "virus": {"suffix": "virus", "priority": 5},
}


def init_genome_dirs() -> None:
    """Ensure genome storage directories exist."""
    GENOMES_DIR.mkdir(parents=True, exist_ok=True)
    GENOMES_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Initialized genome directories: %s", GENOMES_DIR)


def compute_fasta_hash(fasta_path: Path) -> str:
    """Compute SHA-256 hash of FASTA file for integrity checking."""
    sha256 = hashlib.sha256()
    with open(fasta_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def store_genome_metadata(
    genome_id: str,
    organism_name: str,
    organism_type: str,
    taxid: int | None = None,
    gc_content: float | None = None,
    sequence_length: int | None = None,
    strain_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Store genome metadata in SQLite database.

    Args:
        genome_id: Unique identifier (e.g., RefSeq accession)
        organism_name: Full organism name
        organism_type: One of ('bacteria', 'archea', 'fungi', 'protist', 'virus')
        taxid: NCBI taxonomy ID
        gc_content: GC% content (0-100)
        sequence_length: Total sequence length in bp
        strain_id: Optional link to strains table
        metadata: Additional metadata JSON
    """
    if organism_type not in ORGANISM_TYPES:
        raise ValueError(f"Unknown organism_type: {organism_type}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    fasta_path = f"genomes/{organism_type}/{genome_id}.fasta"

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO genomes (
                genome_id, strain_id, organism_name, organism_type,
                taxid, gc_content, sequence_length, fasta_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                genome_id,
                strain_id,
                organism_name,
                organism_type,
                taxid,
                gc_content,
                sequence_length,
                fasta_path,
            ),
        )

        # Store full metadata as JSON for reference
        if metadata:
            meta_path = GENOMES_METADATA_DIR / f"{genome_id}.json"
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

        conn.commit()
        log.debug("Stored genome metadata: %s (%s)", genome_id, organism_type)

    except sqlite3.IntegrityError as e:
        log.error("Failed to store genome %s: %s", genome_id, e)
        raise

    finally:
        conn.close()


def store_genome_growth_observation(
    genome_id: str,
    media_id: str,
    growth: bool,
    growth_rate: str | None = None,
    confidence: float = 1.0,
    source: str = "literature",
) -> None:
    """
    Store a genome-media growth observation.

    Args:
        genome_id: Genome identifier
        media_id: Media identifier
        growth: Whether the organism grows in this media
        growth_rate: Optional growth rate description
        confidence: Confidence score [0-1]
        source: Data source ('literature', 'experiment', 'in_silico')
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO genome_growth (
                genome_id, media_id, growth, growth_rate, confidence, source
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (genome_id, media_id, int(growth), growth_rate, confidence, source),
        )
        conn.commit()
        log.debug("Stored growth observation: %s + %s = %s", genome_id, media_id, growth)

    except sqlite3.Error as e:
        log.error("Failed to store growth observation: %s", e)
        raise

    finally:
        conn.close()


def get_genomes_by_type(organism_type: str) -> list[dict[str, Any]]:
    """Retrieve all genomes of a specific organism type."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM genomes WHERE organism_type = ? ORDER BY gc_content",
            (organism_type,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_genomes_with_growth_data() -> list[dict[str, Any]]:
    """Retrieve all genomes that have associated growth observations."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT DISTINCT g.*, COUNT(gg.media_id) as media_count
            FROM genomes g
            LEFT JOIN genome_growth gg ON g.genome_id = gg.genome_id
            WHERE gg.media_id IS NOT NULL
            GROUP BY g.genome_id
            ORDER BY g.organism_type, media_count DESC
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_genome_count() -> dict[str, int]:
    """Get count of genomes by organism type."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT organism_type, COUNT(*) as count
            FROM genomes
            GROUP BY organism_type
            """
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    finally:
        conn.close()


def log_genome_ingest(task: str, status: str = "done", error_message: str | None = None) -> None:
    """Log genome ingestion task status."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO ingest_log (task, status, error_message)
            VALUES (?, ?, ?)
            """,
            (task, status, error_message),
        )
        conn.commit()

    finally:
        conn.close()
