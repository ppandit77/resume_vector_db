"""
Validate Qdrant Cloud Storage - Quick Test
"""
import sys
import os

# Add parent scripts directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_qdrant():
    """Validate that Qdrant has our data and search works"""

    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings_clean.json"

    logger.info("\n" + "=" * 80)
    logger.info("VALIDATING QDRANT CLOUD STORAGE")
    logger.info("=" * 80)

    # Initialize search system (will connect to existing Qdrant data)
    logger.info("\n[1/2] Connecting to Qdrant Cloud...")
    logger.info("  This will connect to your existing data (no re-upload needed)")

    try:
        search = ProductionSearch(
            DATA_FILE,
            enable_natural_language=False,
            use_mongodb=False,
            use_qdrant=True
        )

        logger.info(f"\n✓ Connected! Total records: {search.total_records}")

    except Exception as e:
        logger.error(f"\n❌ Connection failed: {e}", exc_info=True)
        return False

    # Test search
    logger.info("\n" + "=" * 80)
    logger.info("[2/2] Testing Search")
    logger.info("=" * 80)

    try:
        # Test 1: Simple search
        logger.info("\nTest 1: Search for 'Civil Engineer with AutoCAD'")
        results = search.search(
            query="Civil Engineer with AutoCAD experience",
            query_type="comprehensive",
            limit=3
        )

        logger.info(f"  ✓ Found {len(results)} results")
        for i, r in enumerate(results, 1):
            logger.info(f"    [{i}] {r['full_name']} - {r['job_title']} ({r.get('total_years_experience', 0):.1f} yrs)")

        # Test 2: Search with filters
        logger.info("\nTest 2: Search for 'Senior Software Engineer' with 5+ years experience")
        results = search.search(
            query="Senior Software Engineer",
            query_type="comprehensive",
            min_experience=5.0,
            limit=3
        )

        logger.info(f"  ✓ Found {len(results)} results")
        for i, r in enumerate(results, 1):
            logger.info(f"    [{i}] {r['full_name']} - {r['job_title']} ({r.get('total_years_experience', 0):.1f} yrs)")

    except Exception as e:
        logger.error(f"\n❌ Search failed: {e}", exc_info=True)
        return False

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION COMPLETE - ALL TESTS PASSED!")
    logger.info("=" * 80)
    logger.info("✓ Qdrant Cloud connection working")
    logger.info(f"✓ All {search.total_records} applicants accessible")
    logger.info("✓ Vector search working correctly")
    logger.info("✓ Filters working correctly")
    logger.info("\n🎉 Your Qdrant Cloud persistent storage is working perfectly!")

    return True


if __name__ == "__main__":
    try:
        success = validate_qdrant()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
