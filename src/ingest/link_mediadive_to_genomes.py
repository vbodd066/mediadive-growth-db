"""
Link MediaDive strains to NCBI genomes for integrated training dataset.

This module cross-references existing MediaDive strain-media growth data with NCBI genomes,
creating a rich training dataset that combines:
  - MediaDive: strain species, media formulations, growth conditions (temp, pH, ingredients)
  - NCBI: sequenced genomes for the same species
  - Derived: genome embeddings + media compositions + growth labels

The linking process:
  1. Extract unique species from MediaDive strains table
  2. Search NCBI for reference genomes for each species
  3. Match organisms and link genomes to strains via taxonomy
  4. Populate genome_growth table using existing strain_growth data
  5. Create composite training dataset with media composition vectors

Usage:
  from src.ingest.link_mediadive_to_genomes import (
      extract_mediadive_species,
      link_mediadive_species_to_ncbi,
      propagate_growth_data_to_genomes,
      get_linked_dataset_stats,
  )
  
  # Extract species from MediaDive
  species_list = extract_mediadive_species()
  
  # Link each species to NCBI genomes
  for species in species_list:
      link_mediadive_species_to_ncbi(species)
  
  # Propagate MediaDive growth data to genome level
  propagate_growth_data_to_genomes()
  
  # Check resulting dataset
  stats = get_linked_dataset_stats()
  print(stats)
"""

import sqlite3
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json
from datetime import datetime

from src.config import DB_PATH, NCBI_EMAIL, NCBI_API_KEY
from src.ingest.fetch_ncbi_organisms import (
    ncbi_search,
    ncbi_fetch_summary,
    store_ncbi_organism,
)

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def extract_mediadive_species() -> List[Dict]:
    """
    Extract unique species from MediaDive strains table with metadata.
    
    Returns:
        List of dicts with keys: species, domain, count, strain_ids
        
    Example:
        >>> species_list = extract_mediadive_species()
        >>> for s in species_list:
        ...     print(f"{s['species']}: {s['count']} strains (domain: {s['domain']})")
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT 
        species,
        domain,
        COUNT(strain_id) as count,
        GROUP_CONCAT(strain_id, ',') as strain_ids
    FROM strains
    WHERE species IS NOT NULL AND species != ''
    GROUP BY species, domain
    ORDER BY count DESC
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    species_list = []
    for row in results:
        species_list.append({
            'species': row['species'],
            'domain': row['domain'],
            'count': row['count'],
            'strain_ids': row['strain_ids'].split(',') if row['strain_ids'] else [],
        })
    
    return species_list


def link_mediadive_species_to_ncbi(
    species_name: str,
    domain: Optional[str] = None,
    max_results: int = 3,
) -> Tuple[int, int]:
    """
    Search NCBI for genomes matching a MediaDive species and link them.
    
    Args:
        species_name: Species name from MediaDive (e.g., "Escherichia coli")
        domain: Optional domain (B=bacteria, A=archaea, F=fungi, etc.)
        max_results: Max genomes to link per species
        
    Returns:
        Tuple of (genomes_found, genomes_linked)
        
    Example:
        >>> found, linked = link_mediadive_species_to_ncbi("Bacillus subtilis", domain="B")
        >>> print(f"Found {found}, linked {linked}")
    """
    
    # Build search query
    query = f'"{species_name}"[Organism] AND complete genome'
    
    if domain == 'F':
        query += " AND fungi[Organism]"
    elif domain == 'A':
        query += " AND archaea[Organism]"
    
    logger.info(f"Searching NCBI for: {species_name}")
    
    try:
        # Search assembly database
        uids = ncbi_search("assembly", query, max_results=max_results)
        
        if not uids:
            logger.warning(f"No genomes found for {species_name}")
            return 0, 0
        
        logger.info(f"Found {len(uids)} assemblies for {species_name}")
        
        # Fetch summaries
        summaries = ncbi_fetch_summary("assembly", uids)
        
        if not summaries:
            logger.warning(f"Could not fetch summaries for {species_name}")
            return len(uids), 0
        
        # Link to strains and store genomes
        linked_count = 0
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for summary in summaries:
            try:
                # Extract metadata
                asm_name = summary.get('AssemblyName', '')
                taxid = summary.get('Taxid')
                org_name = summary.get('Organism', '')
                refseq_category = summary.get('RefSeqCategory', '')
                
                # Prefer reference genomes
                if 'reference genome' not in refseq_category.lower():
                    continue
                
                # Store in database
                genome_id = store_ncbi_organism(
                    ncbi_uid=summary.get('AssemblyAccess'),
                    organism_name=org_name,
                    organism_type='bacteria' if domain == 'B' else 'archea' if domain == 'A' else 'fungi' if domain == 'F' else 'other',
                    taxid=taxid,
                    accession=asm_name,
                )
                
                # Link to strains via species name
                link_query = """
                UPDATE genomes 
                SET strain_id = (
                    SELECT strain_id FROM strains 
                    WHERE species = ? AND strain_id IS NOT NULL
                    LIMIT 1
                )
                WHERE genome_id = ? AND strain_id IS NULL
                """
                cursor.execute(link_query, (species_name, genome_id))
                
                linked_count += cursor.rowcount
                
            except Exception as e:
                logger.error(f"Error linking genome for {org_name}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Linked {linked_count} genomes for {species_name}")
        return len(uids), linked_count
        
    except Exception as e:
        logger.error(f"Error searching NCBI for {species_name}: {e}")
        return 0, 0


def propagate_growth_data_to_genomes() -> int:
    """
    Propagate MediaDive strain_growth data to genome_growth table.
    
    For each strain with associated genomes:
      - Copy all strain_growth records to genome_growth
      - Set source='mediadive'
      - Set confidence based on growth_quality
    
    Returns:
        Number of genome_growth records created
        
    Example:
        >>> count = propagate_growth_data_to_genomes()
        >>> print(f"Created {count} genome-media associations")
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query: for each strain with genomes, copy growth data
    copy_query = """
    INSERT OR REPLACE INTO genome_growth 
        (genome_id, media_id, growth, growth_rate, confidence, source)
    SELECT 
        g.genome_id,
        sg.media_id,
        sg.growth,
        sg.growth_rate,
        CASE 
            WHEN sg.growth_quality = 'excellent' THEN 0.95
            WHEN sg.growth_quality = 'good' THEN 0.85
            WHEN sg.growth_quality = 'fair' THEN 0.70
            WHEN sg.growth_quality = 'poor' THEN 0.50
            ELSE 0.75
        END as confidence,
        'mediadive' as source
    FROM genomes g
    JOIN strains s ON g.strain_id = s.strain_id
    JOIN strain_growth sg ON s.strain_id = sg.strain_id
    WHERE g.strain_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM genome_growth 
        WHERE genome_id = g.genome_id 
        AND media_id = sg.media_id 
        AND source = 'mediadive'
    )
    """
    
    cursor.execute(copy_query)
    count = cursor.rowcount
    
    conn.commit()
    logger.info(f"Propagated {count} growth observations to genome_growth")
    
    conn.close()
    return count


def extract_rich_dataset_features() -> Dict:
    """
    Extract rich feature vectors combining genome embeddings + media composition + metadata.
    
    Returns:
        Dict with keys: features, labels, metadata, organism_types
        
    Example:
        >>> data = extract_rich_dataset_features()
        >>> print(f"Dataset size: {len(data['labels'])}")
        >>> print(f"Feature dims: {data['features'].shape}")
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query: get all linked genome-media pairs with embeddings
    query = """
    SELECT 
        gg.genome_id,
        gg.media_id,
        gg.growth,
        gg.confidence,
        gg.source,
        g.organism_type,
        g.organism_name,
        g.gc_content,
        g.sequence_length,
        ge.embedding,
        ge.embedding_dim,
        mc.g_per_l,
        m.min_pH,
        m.max_pH,
        m.media_name
    FROM genome_growth gg
    JOIN genomes g ON gg.genome_id = g.genome_id
    LEFT JOIN genome_embeddings ge ON g.genome_id = ge.genome_id 
        AND ge.embedding_model = 'kmer_128'
    LEFT JOIN media_composition mc ON gg.media_id = mc.media_id
    LEFT JOIN media m ON gg.media_id = m.media_id
    WHERE gg.growth IS NOT NULL
    ORDER BY g.organism_type, gg.genome_id
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        logger.warning("No genome-media pairs found for feature extraction")
        return {
            'features': [],
            'labels': [],
            'metadata': [],
            'organism_types': [],
            'record_count': 0,
        }
    
    # Parse results
    features_list = []
    labels_list = []
    metadata_list = []
    organism_types_list = []
    
    for row in rows:
        # Try to decode embedding (assuming pickled numpy array)
        embedding = None
        if row['embedding']:
            try:
                import pickle
                embedding = pickle.loads(row['embedding'])
            except Exception as e:
                logger.debug(f"Could not decode embedding: {e}")
                continue
        
        if embedding is None:
            continue
        
        features_list.append(embedding)
        labels_list.append(1 if row['growth'] else 0)
        metadata_list.append({
            'genome_id': row['genome_id'],
            'media_id': row['media_id'],
            'organism_name': row['organism_name'],
            'organism_type': row['organism_type'],
            'media_name': row['media_name'],
            'gc_content': row['gc_content'],
            'sequence_length': row['sequence_length'],
            'confidence': row['confidence'],
            'source': row['source'],
        })
        organism_types_list.append(row['organism_type'])
    
    return {
        'features': features_list,
        'labels': labels_list,
        'metadata': metadata_list,
        'organism_types': organism_types_list,
        'record_count': len(features_list),
    }


def get_linked_dataset_stats() -> Dict:
    """
    Get comprehensive statistics on linked MediaDive-NCBI dataset.
    
    Returns:
        Dict with coverage, distribution, and quality metrics
        
    Example:
        >>> stats = get_linked_dataset_stats()
        >>> print(json.dumps(stats, indent=2))
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total strains with genomes
    cursor.execute("""
    SELECT COUNT(DISTINCT s.strain_id) as count
    FROM strains s
    JOIN genomes g ON s.strain_id = g.strain_id
    """)
    strains_with_genomes = cursor.fetchone()['count']
    
    # Total genomes linked
    cursor.execute("SELECT COUNT(*) as count FROM genomes WHERE strain_id IS NOT NULL")
    total_genomes_linked = cursor.fetchone()['count']
    
    # Growth observations propagated
    cursor.execute("""
    SELECT COUNT(*) as count FROM genome_growth WHERE source = 'mediadive'
    """)
    propagated_observations = cursor.fetchone()['count']
    
    # Distribution by organism type
    cursor.execute("""
    SELECT organism_type, COUNT(*) as count
    FROM genomes
    WHERE strain_id IS NOT NULL
    GROUP BY organism_type
    """)
    org_dist = {row['organism_type']: row['count'] for row in cursor.fetchall()}
    
    # Growth rate distribution
    cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN growth = 1 THEN 1 ELSE 0 END) as positive,
        SUM(CASE WHEN growth = 0 THEN 1 ELSE 0 END) as negative
    FROM genome_growth
    WHERE source = 'mediadive'
    """)
    growth_dist = dict(cursor.fetchone())
    
    # Media coverage
    cursor.execute("""
    SELECT COUNT(DISTINCT media_id) as count FROM genome_growth WHERE source = 'mediadive'
    """)
    unique_media = cursor.fetchone()['count']
    
    # Embeddings status
    cursor.execute("""
    SELECT 
        COUNT(DISTINCT g.genome_id) as total_genomes,
        COUNT(DISTINCT CASE WHEN ge.embedding_id IS NOT NULL THEN g.genome_id END) as with_embeddings
    FROM genomes g
    LEFT JOIN genome_embeddings ge ON g.genome_id = ge.genome_id
    WHERE g.strain_id IS NOT NULL
    """)
    embedding_status = dict(cursor.fetchone())
    
    conn.close()
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'mediadive_strains_with_genomes': strains_with_genomes,
            'total_genomes_linked': total_genomes_linked,
            'genome_growth_observations': propagated_observations,
            'unique_media_types': unique_media,
        },
        'organism_distribution': org_dist,
        'growth_distribution': {
            'total_observations': growth_dist['total'],
            'positive_growth': growth_dist['positive'],
            'negative_growth': growth_dist['negative'],
            'positive_ratio': round(growth_dist['positive'] / max(growth_dist['total'], 1), 3),
        },
        'embeddings': {
            'total_genomes': embedding_status['total_genomes'],
            'with_embeddings': embedding_status['with_embeddings'],
            'coverage': round(
                embedding_status['with_embeddings'] / max(embedding_status['total_genomes'], 1),
                3
            ),
        },
    }
    
    return stats


def create_composite_training_dataset() -> str:
    """
    Create a composite training dataset file combining all linked data.
    
    Outputs a JSON file with:
      - Genome-media pairs
      - Growth labels
      - Media composition
      - Temperature, pH metadata
      - Ingredient information
    
    Returns:
        Path to created dataset file
        
    Example:
        >>> dataset_file = create_composite_training_dataset()
        >>> print(f"Created dataset: {dataset_file}")
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query: comprehensive joined data
    query = """
    SELECT 
        g.genome_id,
        s.species,
        s.ccno,
        gg.media_id,
        m.media_name,
        m.min_pH,
        m.max_pH,
        gg.growth,
        gg.confidence,
        g.organism_type,
        g.gc_content,
        g.sequence_length,
        GROUP_CONCAT(DISTINCT i.ingredient_name || '(' || mc.g_per_l || 'g/L)', '; ') as ingredients,
        COUNT(DISTINCT i.ingredient_id) as ingredient_count
    FROM genome_growth gg
    JOIN genomes g ON gg.genome_id = g.genome_id
    JOIN strains s ON g.strain_id = s.strain_id
    JOIN media m ON gg.media_id = m.media_id
    LEFT JOIN media_composition mc ON m.media_id = mc.media_id
    LEFT JOIN ingredients i ON mc.ingredient_id = i.ingredient_id
    WHERE gg.source = 'mediadive'
    GROUP BY g.genome_id, gg.media_id
    ORDER BY g.organism_type, s.species, gg.genome_id
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Build dataset
    dataset = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'total_pairs': len(rows),
            'source': 'mediadive_ncbi_integration',
        },
        'pairs': []
    }
    
    for row in rows:
        dataset['pairs'].append({
            'genome_id': row['genome_id'],
            'species': row['species'],
            'strain_ccno': row['ccno'],
            'media_id': row['media_id'],
            'media_name': row['media_name'],
            'pH_min': row['min_pH'],
            'pH_max': row['max_pH'],
            'growth': bool(row['growth']),
            'confidence': row['confidence'],
            'organism_type': row['organism_type'],
            'genome_gc_content': row['gc_content'],
            'genome_length': row['sequence_length'],
            'ingredients': row['ingredients'],
            'ingredient_count': row['ingredient_count'],
        })
    
    # Save to file
    output_path = Path('data/processed/mediadive_ncbi_integrated_dataset.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)
    
    conn.close()
    logger.info(f"Created composite dataset: {output_path}")
    
    return str(output_path)


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Extract species
    species_list = extract_mediadive_species()
    print(f"\nFound {len(species_list)} unique species in MediaDive")
    print("\nTop species:")
    for s in species_list[:10]:
        print(f"  {s['species']:40} | {s['count']:3} strains | domain: {s['domain']}")
    
    # Link to NCBI (sample)
    print("\n\nLinking to NCBI genomes...")
    for i, s in enumerate(species_list[:5]):  # Sample first 5
        found, linked = link_mediadive_species_to_ncbi(s['species'], s['domain'], max_results=2)
        print(f"  {s['species']:40} | found: {found:3} | linked: {linked:3}")
    
    # Propagate data
    print("\n\nPropagating growth data...")
    count = propagate_growth_data_to_genomes()
    print(f"Created {count} genome-growth associations")
    
    # Statistics
    print("\n\nLinked dataset statistics:")
    stats = get_linked_dataset_stats()
    print(json.dumps(stats, indent=2))
    
    # Create composite dataset
    print("\n\nCreating composite dataset...")
    dataset_file = create_composite_training_dataset()
    print(f"✅ Dataset created: {dataset_file}")
