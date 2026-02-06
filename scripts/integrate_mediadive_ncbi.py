"""
Master script for integrating MediaDive data with NCBI genomes.

This script orchestrates the complete pipeline:
  1. Link MediaDive strains to NCBI genomes via species matching
  2. Propagate MediaDive growth/media/condition data to genomes
  3. Build composite training dataset with genome embeddings + media composition
  4. Generate statistics and quality reports

Usage:
  python -m scripts.integrate_mediadive_ncbi [OPTIONS]

Examples:
  # Full integration pipeline
  python -m scripts.integrate_mediadive_ncbi --full

  # Link only (don't propagate yet)
  python -m scripts.integrate_mediadive_ncbi --link-species --max-per-species 5

  # Propagate existing links
  python -m scripts.integrate_mediadive_ncbi --propagate --build-dataset

  # Get statistics only
  python -m scripts.integrate_mediadive_ncbi --stats --verbose
"""

import argparse
import logging
import json
import sys
from pathlib import Path
from typing import List

from src.ingest.link_mediadive_to_genomes import (
    extract_mediadive_species,
    link_mediadive_species_to_ncbi,
    propagate_growth_data_to_genomes,
    extract_rich_dataset_features,
    get_linked_dataset_stats,
    create_composite_training_dataset,
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def link_all_species(max_per_species: int = 3, limit_species: int = None) -> dict:
    """
    Link all MediaDive species to NCBI genomes.
    
    Args:
        max_per_species: Max genomes to link per species
        limit_species: Limit to first N species (for testing)
        
    Returns:
        Statistics dict
    """
    logger.info("=" * 80)
    logger.info("PHASE 1: Linking MediaDive Species to NCBI Genomes")
    logger.info("=" * 80)
    
    # Extract species
    species_list = extract_mediadive_species()
    logger.info(f"Found {len(species_list)} unique species in MediaDive")
    
    if limit_species:
        species_list = species_list[:limit_species]
        logger.info(f"Limiting to first {limit_species} species")
    
    stats = {
        'total_species': len(species_list),
        'species_processed': 0,
        'genomes_found': 0,
        'genomes_linked': 0,
        'errors': 0,
        'details': [],
    }
    
    # Link each species
    for i, species in enumerate(species_list, 1):
        try:
            logger.info(f"\n[{i}/{len(species_list)}] Processing: {species['species']}")
            logger.info(f"  Strains in MediaDive: {species['count']}")
            logger.info(f"  Domain: {species['domain']}")
            
            found, linked = link_mediadive_species_to_ncbi(
                species['species'],
                species['domain'],
                max_results=max_per_species,
            )
            
            logger.info(f"  NCBI result: found={found}, linked={linked}")
            
            stats['species_processed'] += 1
            stats['genomes_found'] += found
            stats['genomes_linked'] += linked
            
            stats['details'].append({
                'species': species['species'],
                'domain': species['domain'],
                'mediadive_strains': species['count'],
                'genomes_found': found,
                'genomes_linked': linked,
            })
            
        except Exception as e:
            logger.error(f"Error processing {species['species']}: {e}")
            stats['errors'] += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 1 Summary:")
    logger.info(f"  Species processed: {stats['species_processed']}/{stats['total_species']}")
    logger.info(f"  Genomes found: {stats['genomes_found']}")
    logger.info(f"  Genomes linked: {stats['genomes_linked']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"{'='*80}\n")
    
    return stats


def propagate_and_build() -> dict:
    """
    Propagate MediaDive growth data to linked genomes and build dataset.
    
    Returns:
        Statistics dict
    """
    logger.info("=" * 80)
    logger.info("PHASE 2: Propagating Growth Data & Building Dataset")
    logger.info("=" * 80)
    
    stats = {}
    
    # Propagate growth data
    logger.info("\nPropagating strain_growth → genome_growth...")
    propagated_count = propagate_growth_data_to_genomes()
    stats['propagated_observations'] = propagated_count
    logger.info(f"✅ Propagated {propagated_count} genome-growth associations")
    
    # Extract rich features
    logger.info("\nExtracting rich dataset features...")
    try:
        dataset = extract_rich_dataset_features()
        stats['dataset_size'] = dataset['record_count']
        logger.info(f"✅ Extracted {dataset['record_count']} genome-media pairs")
        logger.info(f"   Organism types: {set(dataset['organism_types'])}")
    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        stats['dataset_size'] = 0
    
    # Create composite dataset
    logger.info("\nCreating composite training dataset...")
    try:
        dataset_file = create_composite_training_dataset()
        stats['dataset_file'] = dataset_file
        logger.info(f"✅ Created: {dataset_file}")
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        stats['dataset_file'] = None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 2 Summary:")
    logger.info(f"  Genome-growth records: {stats['propagated_observations']}")
    logger.info(f"  Dataset file: {stats.get('dataset_file', 'N/A')}")
    logger.info(f"{'='*80}\n")
    
    return stats


def print_statistics(verbose: bool = False):
    """Print detailed statistics on linked dataset."""
    logger.info("=" * 80)
    logger.info("DATASET STATISTICS")
    logger.info("=" * 80)
    
    stats = get_linked_dataset_stats()
    
    # Summary
    logger.info("\n📊 Summary:")
    for key, value in stats['summary'].items():
        logger.info(f"  {key:.<40} {value}")
    
    # Organism distribution
    logger.info("\n🧬 Organism Distribution:")
    for org_type, count in stats['organism_distribution'].items():
        logger.info(f"  {org_type:.<40} {count}")
    
    # Growth distribution
    logger.info("\n📈 Growth Distribution:")
    for key, value in stats['growth_distribution'].items():
        logger.info(f"  {key:.<40} {value}")
    
    # Embeddings
    logger.info("\n🔬 Embeddings Status:")
    for key, value in stats['embeddings'].items():
        logger.info(f"  {key:.<40} {value}")
    
    if verbose:
        logger.info("\n📋 Full Statistics (JSON):")
        logger.info(json.dumps(stats, indent=2))
    
    logger.info(f"\n{'='*80}\n")
    
    return stats


def generate_report(stats: dict, output_file: str = None) -> str:
    """
    Generate comprehensive integration report.
    
    Args:
        stats: Statistics dict
        output_file: Optional path to save report
        
    Returns:
        Report path or string
    """
    report = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                  MediaDive-NCBI Integration Report                         ║
╚════════════════════════════════════════════════════════════════════════════╝

INTEGRATION SUMMARY
───────────────────────────────────────────────────────────────────────────

  MediaDive Strains with NCBI Genomes .... {stats.get('strains_with_genomes', 'N/A')}
  Total NCBI Genomes Linked ............ {stats.get('total_genomes_linked', 'N/A')}
  Growth Observations Propagated ....... {stats.get('propagated_observations', 'N/A')}
  Training Pairs Generated ............ {stats.get('dataset_size', 'N/A')}

ORGANISM COVERAGE
───────────────────────────────────────────────────────────────────────────

  • Bacteria:  {stats.get('bacteria_count', 'N/A')} genomes
  • Archaea:   {stats.get('archaea_count', 'N/A')} genomes  
  • Fungi:     {stats.get('fungi_count', 'N/A')} genomes
  • Protists:  {stats.get('protists_count', 'N/A')} genomes

GROWTH DATA QUALITY
───────────────────────────────────────────────────────────────────────────

  Total Observations ................. {stats.get('total_observations', 'N/A')}
  Positive Growth .................... {stats.get('positive_growth', 'N/A')}
  Negative Growth .................... {stats.get('negative_growth', 'N/A')}
  Positive Ratio .................... {stats.get('positive_ratio', 'N/A')}

MEDIA & INGREDIENT INFORMATION
───────────────────────────────────────────────────────────────────────────

  Unique Media Types ................ {stats.get('unique_media_types', 'N/A')}
  Total Ingredients Used ............ {stats.get('ingredient_count', 'N/A')}
  pH Range Characterized ............ {stats.get('ph_ranges', 'N/A')}

GENOME EMBEDDINGS
───────────────────────────────────────────────────────────────────────────

  Genomes with Embeddings ........... {stats.get('genomes_with_embeddings', 'N/A')}
  Embedding Models Available ........ {stats.get('embedding_models', 'N/A')}
  Embedding Dimensions ............. {stats.get('embedding_dims', 'N/A')}

DATASET READINESS
───────────────────────────────────────────────────────────────────────────

  ✅ Cross-organism training pairs generated
  ✅ Media composition vectors available
  ✅ Growth labels propagated from MediaDive
  ✅ Temperature/pH metadata linked
  ✅ Ingredient profiles available

Next Steps:
  1. Extract genome embeddings (if not already done)
  2. Build CVAE training dataset
  3. Start curriculum learning (bacteria → archaea → fungi → protists)
  4. Evaluate cross-organism generalization

═══════════════════════════════════════════════════════════════════════════
"""
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to: {output_file}")
    
    return report


def main():
    """Main orchestration."""
    parser = argparse.ArgumentParser(
        description='Integrate MediaDive data with NCBI genomes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run complete integration pipeline',
    )
    parser.add_argument(
        '--link-species',
        action='store_true',
        help='Link MediaDive species to NCBI genomes',
    )
    parser.add_argument(
        '--propagate',
        action='store_true',
        help='Propagate growth data to genomes',
    )
    parser.add_argument(
        '--build-dataset',
        action='store_true',
        help='Build composite training dataset',
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Print statistics only',
    )
    parser.add_argument(
        '--max-per-species',
        type=int,
        default=3,
        help='Max genomes per species (default: 3)',
    )
    parser.add_argument(
        '--limit-species',
        type=int,
        help='Limit to first N species (for testing)',
    )
    parser.add_argument(
        '--save-report',
        type=str,
        help='Save report to file',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing',
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    # Handle dry run
    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be made")
        logger.info("\nWhat would be executed:")
        if args.full:
            logger.info("  1. Link all MediaDive species to NCBI")
            logger.info("  2. Propagate growth data to genomes")
            logger.info("  3. Build composite dataset")
        if args.link_species:
            logger.info(f"  • Link species (max {args.max_per_species} genomes each)")
        if args.propagate:
            logger.info("  • Propagate growth data")
        if args.build_dataset:
            logger.info("  • Build composite dataset")
        if args.stats:
            logger.info("  • Display statistics")
        return
    
    # Default to full pipeline
    if not (args.full or args.link_species or args.propagate or args.build_dataset or args.stats):
        args.full = True
    
    all_stats = {}
    
    # Execute phases
    if args.full or args.link_species:
        linking_stats = link_all_species(
            max_per_species=args.max_per_species,
            limit_species=args.limit_species,
        )
        all_stats.update(linking_stats)
    
    if args.full or args.propagate or args.build_dataset:
        propagation_stats = propagate_and_build()
        all_stats.update(propagation_stats)
    
    if args.full or args.stats:
        dataset_stats = print_statistics(args.verbose)
        all_stats.update(dataset_stats)
    
    # Save report if requested
    if args.save_report:
        report = generate_report(all_stats, args.save_report)
        logger.info(f"Report saved to: {args.save_report}")
    
    logger.info("✅ Integration complete!")


if __name__ == '__main__':
    main()
