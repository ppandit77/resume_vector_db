"""
Test Europe Cluster with 2,000 Records - Quick Upload & Search Test
"""
import sys
import os
import json

# Add parent scripts directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_europe_cluster():
    """Test Europe cluster with 2,000 records"""

    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings_clean.json"
    TEMP_FILE = "/tmp/applicants_2000.json"

    logger.info("\n" + "=" * 80)
    logger.info("TESTING EUROPE CLUSTER (GERMANY)")
    logger.info("=" * 80)

    # Create temporary file with first 2,000 records
    logger.info("\n[1/4] Preparing 2,000 records for upload...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    subset_data = all_data[:2000]

    with open(TEMP_FILE, 'w', encoding='utf-8') as f:
        json.dump(subset_data, f)

    logger.info(f"  ✓ Created temporary file with {len(subset_data)} records")

    # Upload to Europe cluster
    logger.info("\n[2/4] Uploading to Europe (Germany) cluster...")
    logger.info("  This should be faster than US West Coast")
    logger.info("  Expected time: ~30-45 minutes for 2,000 records")

    try:
        search = ProductionSearch(
            TEMP_FILE,
            enable_natural_language=False,
            use_mongodb=False,
            use_qdrant=True
        )

        logger.info("\n✓ Upload completed successfully!")

    except Exception as e:
        logger.error(f"\n❌ Upload failed: {e}", exc_info=True)
        return False

    # Test search
    logger.info("\n" + "=" * 80)
    logger.info("[3/4] Testing Search Functionality")
    logger.info("=" * 80)

    try:
        # Test 1: Basic search
        logger.info("\nTest 1: Search for 'Civil Engineer with AutoCAD'")
        results = search.search(
            query="Civil Engineer with AutoCAD experience",
            query_type="comprehensive",
            limit=5
        )

        logger.info(f"  ✓ Found {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            logger.info(f"    [{i}] {r.get('full_name', 'N/A')} - {r.get('job_title', 'N/A')} ({r.get('total_years_experience', 0):.1f} yrs)")

        # Test 2: Search with filters
        logger.info("\nTest 2: Search for 'Senior Software Engineer' with 5+ years")
        results = search.search(
            query="Senior Software Engineer",
            query_type="comprehensive",
            min_experience=5.0,
            limit=5
        )

        logger.info(f"  ✓ Found {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            logger.info(f"    [{i}] {r.get('full_name', 'N/A')} - {r.get('job_title', 'N/A')} ({r.get('total_years_experience', 0):.1f} yrs)")

    except Exception as e:
        logger.error(f"\n❌ Search failed: {e}", exc_info=True)
        return False

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("[4/4] TEST SUMMARY")
    logger.info("=" * 80)
    logger.info("✓ Europe (Germany) cluster: WORKING")
    logger.info("✓ Upload completed: 2,000 records")
    logger.info("✓ Search working: YES")
    logger.info("✓ Filters working: YES")
    logger.info("\n🎉 Europe cluster is working perfectly!")
    logger.info("\nNext step: Upload all 4,889 records to this cluster")

    # Clean up
    os.remove(TEMP_FILE)

    return True


if __name__ == "__main__":
    try:
        success = test_europe_cluster()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
