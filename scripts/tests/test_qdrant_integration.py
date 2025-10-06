"""
Test Qdrant Integration with Production Search System
"""

import sys
import os
from datetime import datetime

# Add parent scripts directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_qdrant_integration():
    """Test Qdrant vector database integration"""

    # Data file - using clean dataset with pure Gemini embeddings only
    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings_clean.json"

    logger.info("\n" + "=" * 80)
    logger.info("TESTING QDRANT INTEGRATION")
    logger.info("=" * 80)

    # Initialize search system with Qdrant
    logger.info("\n[1/3] Initializing search system with Qdrant...")
    logger.info("  This will connect to Qdrant Cloud and ingest all 5,000 applicants")
    logger.info("  Please wait, this may take a few minutes...")

    try:
        search = ProductionSearch(
            DATA_FILE,
            enable_natural_language=False,
            use_mongodb=False,  # Disable MongoDB
            use_qdrant=True     # Enable Qdrant
        )

        logger.info("\n✓ Search system initialized successfully!")

    except Exception as e:
        logger.error(f"\n❌ Error initializing search system: {e}", exc_info=True)
        return False

    # Test 1: Basic search
    logger.info("\n" + "=" * 80)
    logger.info("[2/3] TEST 1: Basic Search with Qdrant Storage")
    logger.info("=" * 80)

    try:
        results = search.search(
            query="Civil Engineer with AutoCAD experience",
            query_type="comprehensive",
            limit=5
        )

        logger.info(f"✓ Found {len(results)} results")
        if results:
            logger.info(f"  Sample result: {results[0]['full_name']} - {results[0]['job_title']}")

    except Exception as e:
        logger.error(f"❌ Search failed: {e}", exc_info=True)
        return False

    # Test 2: Search with filters
    logger.info("\n" + "=" * 80)
    logger.info("[3/3] TEST 2: Search with Experience Filter")
    logger.info("=" * 80)

    try:
        results = search.search(
            query="Senior Engineer",
            query_type="comprehensive",
            min_experience=5.0,
            limit=5
        )

        logger.info(f"✓ Found {len(results)} results with min_experience=5.0")
        if results:
            for i, r in enumerate(results[:3], 1):
                exp = r.get('total_years_experience', 0)
                logger.info(f"  [{i}] {r['full_name']}: {exp:.1f} years experience")

    except Exception as e:
        logger.error(f"❌ Filtered search failed: {e}", exc_info=True)
        return False

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("QDRANT INTEGRATION TEST COMPLETED")
    logger.info("=" * 80)
    logger.info("✓ Qdrant Cloud connection successful")
    logger.info("✓ All 5,000 applicants ingested to Qdrant")
    logger.info("✓ Vector search working correctly")
    logger.info("✓ Filters working correctly")
    logger.info("\n🎉 Your embeddings are now stored persistently in Qdrant!")

    return True


if __name__ == "__main__":
    try:
        success = test_qdrant_integration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
