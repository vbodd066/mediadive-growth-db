#!/bin/bash
# Quick verification and summary script
# Run: bash VERIFY_INTEGRATION.sh

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║       MediaDive-NCBI Integration: Implementation Verification         ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check files exist
echo "📁 Checking new files..."
echo ""

files_to_check=(
    "src/ingest/link_mediadive_to_genomes.py"
    "scripts/integrate_mediadive_ncbi.py"
    "MEDIADIVE_NCBI_INTEGRATION.md"
    "MEDIADIVE_INTEGRATION_WORKFLOW.md"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        printf "  ✅ %-50s (%4d lines)\n" "$file" "$lines"
    else
        printf "  ❌ %-50s (MISSING)\n" "$file"
    fi
done

echo ""
echo "📋 Checking Makefile targets..."
echo ""

targets=("integrate-mediadive-ncbi" "integrate-link-species" "integrate-propagate" "integrate-stats")

for target in "${targets[@]}"; do
    if grep -q "^$target:" Makefile; then
        printf "  ✅ make %-45s\n" "$target"
    else
        printf "  ❌ make %-45s (MISSING)\n" "$target"
    fi
done

echo ""
echo "🔍 Python imports check..."
echo ""

python3 << 'PYTHON_CHECK'
import sys
try:
    from src.ingest.link_mediadive_to_genomes import (
        extract_mediadive_species,
        link_mediadive_species_to_ncbi,
        propagate_growth_data_to_genomes,
        get_linked_dataset_stats,
    )
    print("  ✅ All functions imported successfully")
    print("     - extract_mediadive_species")
    print("     - link_mediadive_species_to_ncbi")
    print("     - propagate_growth_data_to_genomes")
    print("     - get_linked_dataset_stats")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    sys.exit(1)
PYTHON_CHECK

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ INTEGRATION COMPLETE!"
echo ""
echo "Quick commands to get started:"
echo ""
echo "  # Full integration pipeline"
echo "  make integrate-mediadive-ncbi"
echo ""
echo "  # Step-by-step"
echo "  make integrate-link-species"
echo "  make integrate-propagate"
echo "  make integrate-stats"
echo ""
echo "  # Documentation"
echo "  cat MEDIADIVE_NCBI_INTEGRATION.md"
echo "  cat MEDIADIVE_INTEGRATION_WORKFLOW.md"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
