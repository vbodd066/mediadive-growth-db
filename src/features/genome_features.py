"""
Genome feature extraction and embedding generation.

Supports multiple embedding strategies:
1. **Kmer profiles**: Extract k-mer frequencies from sequence
2. **GC content + basic stats**: Simple but informative features
3. **ORF-based features**: Open reading frame analysis
4. **Pre-trained models**: Use ProtTrans/AlphaFold embeddings (future)
"""

from __future__ import annotations

import logging
import sqlite3
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from src.config import DB_PATH, RAW_DIR

log = logging.getLogger(__name__)

GENOMES_DIR = RAW_DIR / "genomes"


def extract_kmers(sequence: str, k: int = 6) -> dict[str, int]:
    """
    Extract k-mer frequency profile from DNA sequence.

    Args:
        sequence: DNA sequence (uppercase, no ambiguity codes expected)
        k: k-mer size

    Returns:
        Dictionary mapping k-mers to frequencies
    """
    kmers = {}
    sequence = sequence.upper()

    for i in range(len(sequence) - k + 1):
        kmer = sequence[i : i + k]
        if "N" not in kmer:  # skip ambiguous
            kmers[kmer] = kmers.get(kmer, 0) + 1

    return kmers


def normalize_kmer_profile(kmers: dict[str, int], total_bases: int) -> np.ndarray:
    """
    Convert k-mer frequencies to normalized vector.

    Returns vector of shape (4^k,) with normalized frequencies for all possible k-mers.
    """
    k = len(next(iter(kmers.keys())))
    all_kmers = []

    # Generate all possible k-mers
    def generate_kmers_recursive(current: str = "", depth: int = 0) -> None:
        if depth == k:
            all_kmers.append(current)
        else:
            for base in "ACGT":
                generate_kmers_recursive(current + base, depth + 1)

    generate_kmers_recursive()

    # Create normalized vector
    profile = np.zeros(len(all_kmers), dtype=np.float32)
    for idx, kmer in enumerate(all_kmers):
        profile[idx] = kmers.get(kmer, 0) / max(1, total_bases - k + 1)

    return profile


def compute_sequence_stats(sequence: str) -> dict[str, float]:
    """
    Compute basic sequence statistics.

    Returns:
        Dict with: gc_content, at_content, n_count, sequence_length
    """
    sequence = sequence.upper()
    seq_len = len(sequence)

    gc_count = sequence.count("G") + sequence.count("C")
    at_count = sequence.count("A") + sequence.count("T")
    n_count = sequence.count("N")

    return {
        "gc_content": 100.0 * gc_count / seq_len if seq_len > 0 else 0.0,
        "at_content": 100.0 * at_count / seq_len if seq_len > 0 else 0.0,
        "n_count": n_count,
        "sequence_length": seq_len,
    }


def read_fasta(fasta_path: Path) -> tuple[str, str]:
    """
    Read FASTA file and return (header, sequence).

    Only reads first sequence if multiple present.
    """
    header = ""
    sequence = ""

    with open(fasta_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if sequence:  # Already read first seq
                    break
                header = line[1:]  # Remove '>'
            else:
                sequence += line

    return header, sequence


def compute_genome_embedding(
    genome_id: str,
    fasta_path: Path,
    method: str = "kmer_128",
) -> np.ndarray:
    """
    Compute embedding for a genome.

    Args:
        genome_id: Genome identifier
        fasta_path: Path to FASTA file
        method: Embedding method ('kmer_64', 'kmer_128', 'kmer_256', 'stats')

    Returns:
        Embedding vector (numpy array)
    """
    if not fasta_path.exists():
        raise FileNotFoundError(f"FASTA file not found: {fasta_path}")

    log.info("Computing %s embedding for %s", method, genome_id)

    header, sequence = read_fasta(fasta_path)
    if not sequence:
        raise ValueError(f"No sequence found in {fasta_path}")

    if method.startswith("kmer_"):
        k = int(method.split("_")[1])
        kmers = extract_kmers(sequence, k=k)
        embedding = normalize_kmer_profile(kmers, len(sequence))

    elif method == "stats":
        stats = compute_sequence_stats(sequence)
        embedding = np.array(
            [
                stats["gc_content"],
                stats["at_content"],
                np.log10(stats["sequence_length"]),
                stats["n_count"],
            ],
            dtype=np.float32,
        )

    else:
        raise ValueError(f"Unknown embedding method: {method}")

    return embedding


def store_genome_embedding(
    genome_id: str,
    embedding: np.ndarray,
    method: str = "kmer_128",
) -> None:
    """
    Store computed embedding in database.

    Args:
        genome_id: Genome identifier
        embedding: Embedding vector (numpy array)
        method: Embedding method name
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    embedding_bytes = pickle.dumps(embedding)
    embedding_dim = embedding.shape[0] if embedding.ndim > 0 else 1

    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO genome_embeddings (
                genome_id, embedding_model, embedding, embedding_dim
            ) VALUES (?, ?, ?, ?)
            """,
            (genome_id, method, embedding_bytes, embedding_dim),
        )
        conn.commit()
        log.debug("Stored embedding for %s (%s): dim=%d", genome_id, method, embedding_dim)

    except sqlite3.Error as e:
        log.error("Failed to store embedding: %s", e)
        raise

    finally:
        conn.close()


def load_genome_embedding(
    genome_id: str,
    method: str = "kmer_128",
) -> np.ndarray | None:
    """Load pre-computed embedding from database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT embedding FROM genome_embeddings
            WHERE genome_id = ? AND embedding_model = ?
            """,
            (genome_id, method),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return pickle.loads(row[0])

    finally:
        conn.close()


def build_genome_embedding_matrix(
    organism_type: str | None = None,
    method: str = "kmer_128",
) -> tuple[np.ndarray, list[str]]:
    """
    Build embedding matrix for all genomes (or specific organism type).

    Returns:
        Tuple of (embedding_matrix, genome_ids)
        Matrix shape: (n_genomes, embedding_dim)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if organism_type:
            cursor.execute(
                """
                SELECT genome_id FROM genomes
                WHERE organism_type = ?
                ORDER BY genome_id
                """,
                (organism_type,),
            )
        else:
            cursor.execute("SELECT genome_id FROM genomes ORDER BY genome_id")

        genome_ids = [row[0] for row in cursor.fetchall()]

        if not genome_ids:
            log.warning("No genomes found for organism_type=%s", organism_type)
            return np.array([]), []

        embeddings = []
        missing = []

        for genome_id in genome_ids:
            emb = load_genome_embedding(genome_id, method=method)
            if emb is None:
                missing.append(genome_id)
                # Use zero embedding as placeholder
                emb = np.zeros(256, dtype=np.float32)  # Assume 256-dim

            embeddings.append(emb)

        if missing:
            log.warning("Missing embeddings for %d genomes (using zeros as placeholders)", len(missing))

        matrix = np.stack(embeddings)
        log.info("Built embedding matrix: shape=%s, method=%s, missing=%d", matrix.shape, method, len(missing))

        return matrix, genome_ids

    finally:
        conn.close()


def compute_all_genome_embeddings(method: str = "kmer_128") -> int:
    """
    Compute and store embeddings for all genomes.

    Returns:
        Number of embeddings computed
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT genome_id, fasta_path, organism_type
            FROM genomes
            WHERE genome_id NOT IN (
                SELECT genome_id FROM genome_embeddings WHERE embedding_model = ?
            )
            """,
            (method,),
        )

        genomes = cursor.fetchall()
        count = 0

        for genome_id, fasta_rel, organism_type in genomes:
            try:
                fasta_path = GENOMES_DIR / fasta_rel
                embedding = compute_genome_embedding(genome_id, fasta_path, method=method)
                store_genome_embedding(genome_id, embedding, method=method)
                count += 1

                if count % 100 == 0:
                    log.info("Computed %d embeddings so far...", count)

            except Exception as e:
                log.error("Failed to compute embedding for %s: %s", genome_id, e)
                continue

        log.info("Computed total of %d new embeddings", count)
        return count

    finally:
        conn.close()
