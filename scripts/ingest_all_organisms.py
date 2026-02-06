#!/usr/bin/env python3
"""
Master ingest script for comprehensive organism and growth data collection.

Orchestrates data collection from multiple sources:
1. **BacDive** - Bacterial culturomics data
2. **NCBI** - Fungal, protist, and archeal genome metadata
3. **PubMed** - Growth condition literature
4. **Curated datasets** - Manual organism-media mappings

Usage:
    python -m scripts.ingest_all_organisms --help
    python -m scripts.ingest_all_organisms --bacteria --fungi --protists
    python -m scripts.ingest_all_organisms --bacdive-query "Escherichia"
    python -m scripts.ingest_all_organisms --all

Progress is tracked in the ingest_log table for resumability.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from src.ingest.fetch_bacdive import (
    init_bacdive_dirs,
    search_and_ingest_bacdive,
    get_bacdive_statistics,
    log_bacdive_ingest,
)
from src.ingest.fetch_ncbi_organisms import (
    init_ncbi_dirs,
    ingest_fungal_species,
    ingest_protist_species,
    get_ncbi_statistics,
    log_ncbi_ingest,
)
from src.ingest.enrich_growth_conditions import (
    enrich_organism_conditions,
    create_curated_growth_map,
    link_organism_to_media,
    get_enrichment_statistics,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
log = logging.getLogger(__name__)


def print_statistics(stage: str) -> None:
    """Print ingestion statistics."""
    print(f"\n{'='*60}")
    print(f"Statistics after {stage}")
    print(f"{'='*60}")

    bacdive_stats = get_bacdive_statistics()
    print(f"BacDive strains: {bacdive_stats.get('total_bacdive_strains', 0)}")
    if bacdive_stats.get('by_domain'):
        for domain, count in bacdive_stats['by_domain'].items():
            print(f"  {domain}: {count}")

    ncbi_stats = get_ncbi_statistics()
    print(f"\nNCBI organisms:")
    for org_type, count in ncbi_stats.items():
        print(f"  {org_type}: {count}")

    enrichment_stats = get_enrichment_statistics()
    print(f"\nGrowth condition links:")
    for source, count in enrichment_stats.items():
        print(f"  {source}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Comprehensive organism and growth data ingestion pipeline"
    )

    # Data sources
    parser.add_argument(
        "--bacteria",
        action="store_true",
        help="Ingest bacterial data from BacDive",
    )
    parser.add_argument(
        "--fungi",
        action="store_true",
        help="Ingest fungal genomes from NCBI",
    )
    parser.add_argument(
        "--protists",
        action="store_true",
        help="Ingest protist genomes from NCBI",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest from all sources (bacteria, fungi, protists)",
    )

    # BacDive options
    parser.add_argument(
        "--bacdive-query",
        default="bacteria",
        help="BacDive search query (default: 'bacteria')",
    )
    parser.add_argument(
        "--bacdive-limit",
        type=int,
        default=100,
        help="Max BacDive strains to ingest",
    )

    # NCBI options
    parser.add_argument(
        "--fungal-genus",
        default=None,
        help="Filter fungi to specific genus (e.g., 'Saccharomyces')",
    )
    parser.add_argument(
        "--ncbi-limit",
        type=int,
        default=100,
        help="Max NCBI genomes per organism type",
    )

    # Enrichment options
    parser.add_argument(
        "--enrich-conditions",
        action="store_true",
        help="Enrich organisms with growth conditions from literature",
    )
    parser.add_argument(
        "--apply-curated",
        action="store_true",
        help="Apply curated organism-media mappings",
    )

    args = parser.parse_args()

    # Determine what to ingest
    ingest_bacteria = args.bacteria or args.all
    ingest_fungi = args.fungi or args.all
    ingest_protists = args.protists or args.all

    log.info("="*70)
    log.info("COMPREHENSIVE ORGANISM INGESTION PIPELINE")
    log.info("="*70)
    log.info("Configuration:")
    log.info("  Bacteria: %s", ingest_bacteria)
    log.info("  Fungi: %s", ingest_fungi)
    log.info("  Protists: %s", ingest_protists)
    log.info("  Enrich conditions: %s", args.enrich_conditions)
    log.info("  Apply curated mappings: %s", args.apply_curated)
    log.info("")

    start_time = time.time()

    try:
        # ────────────────────────────────────────────────────────
        # Initialize directories
        # ────────────────────────────────────────────────────────
        log.info("Initializing data directories...")
        init_bacdive_dirs()
        init_ncbi_dirs()

        # ────────────────────────────────────────────────────────
        # Bacterial data (BacDive)
        # ────────────────────────────────────────────────────────
        if ingest_bacteria:
            log.info("\n" + "="*70)
            log.info("INGESTING BACTERIAL DATA FROM BACDIVE")
            log.info("="*70)

            try:
                bacdive_ingested = search_and_ingest_bacdive(
                    query=args.bacdive_query,
                    organism_type="bacteria",
                    limit=args.bacdive_limit,
                )
                log.info("✓ Ingested %d bacterial strains from BacDive", bacdive_ingested)
                log_bacdive_ingest("ingest_bacteria", status="done")

            except Exception as e:
                log.error("✗ BacDive ingestion failed: %s", e, exc_info=True)
                log_bacdive_ingest("ingest_bacteria", status="error", error_message=str(e))
                if not (ingest_fungi or ingest_protists):
                    return 1

        # ────────────────────────────────────────────────────────
        # Fungal data (NCBI)
        # ────────────────────────────────────────────────────────
        if ingest_fungi:
            log.info("\n" + "="*70)
            log.info("INGESTING FUNGAL GENOMES FROM NCBI")
            log.info("="*70)

            try:
                fungi_ingested = ingest_fungal_species(
                    genus=args.fungal_genus,
                    limit=args.ncbi_limit,
                )
                log.info("✓ Ingested %d fungal genomes from NCBI", fungi_ingested)
                log_ncbi_ingest("ingest_fungi", status="done")

            except Exception as e:
                log.error("✗ Fungal NCBI ingestion failed: %s", e, exc_info=True)
                log_ncbi_ingest("ingest_fungi", status="error", error_message=str(e))

        # ────────────────────────────────────────────────────────
        # Protist data (NCBI)
        # ────────────────────────────────────────────────────────
        if ingest_protists:
            log.info("\n" + "="*70)
            log.info("INGESTING PROTIST GENOMES FROM NCBI")
            log.info("="*70)

            try:
                protist_ingested = ingest_protist_species(limit=args.ncbi_limit)
                log.info("✓ Ingested %d protist genomes from NCBI", protist_ingested)
                log_ncbi_ingest("ingest_protists", status="done")

            except Exception as e:
                log.error("✗ Protist NCBI ingestion failed: %s", e, exc_info=True)
                log_ncbi_ingest("ingest_protists", status="error", error_message=str(e))

        # ────────────────────────────────────────────────────────
        # Growth condition enrichment
        # ────────────────────────────────────────────────────────
        if args.enrich_conditions:
            log.info("\n" + "="*70)
            log.info("ENRICHING GROWTH CONDITIONS FROM LITERATURE")
            log.info("="*70)

            # This would iterate over organisms and enrich them
            # For now, log as planned
            log.info("Growth condition enrichment scheduled for future implementation")

        # ────────────────────────────────────────────────────────
        # Curated organism-media mappings
        # ────────────────────────────────────────────────────────
        if args.apply_curated:
            log.info("\n" + "="*70)
            log.info("APPLYING CURATED ORGANISM-MEDIA MAPPINGS")
            log.info("="*70)

            curated_map = create_curated_growth_map()
            linked = 0

            for organism_pattern, media_list in curated_map.items():
                for media_id, confidence in media_list:
                    if link_organism_to_media(
                        organism_name=organism_pattern,
                        media_id=media_id,
                        growth=True,
                        confidence=confidence,
                        source="curated",
                    ):
                        linked += 1

            log.info("✓ Applied %d curated organism-media links", linked)

        # ────────────────────────────────────────────────────────
        # Print statistics
        # ────────────────────────────────────────────────────────
        print_statistics("ingestion complete")

        elapsed = time.time() - start_time
        log.info("")
        log.info("="*70)
        log.info("INGESTION PIPELINE COMPLETE in %.1f seconds", elapsed)
        log.info("="*70)

        return 0

    except Exception as e:
        log.error("Ingestion pipeline failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
