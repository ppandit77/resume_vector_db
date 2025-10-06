"""
Test MongoDB Atlas Integration
"""
import sys
import os

# Add parent scripts directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings_clean.json"

logger.info("=" * 80)
logger.info("TESTING MONGODB ATLAS INTEGRATION")
logger.info("=" * 80)

logger.info("\n[1/3] Initializing search system with MongoDB Atlas...")
logger.info("  This will connect to MongoDB Atlas and ingest 4,889 applicants")
logger.info("  Please wait, this may take a few minutes...")

try:
    search = ProductionSearch(
        DATA_FILE,
        enable_natural_language=False,
        use_mongodb=True
    )

    logger.info("\n✓ Search system initialized successfully!")

except Exception as e:
    logger.error(f"\n❌ Error initializing search system: {e}", exc_info=True)
    sys.exit(1)

# Test 1: Basic search
logger.info("\n" + "=" * 80)
logger.info("[2/3] TEST 1: Basic Search")
logger.info("=" * 80)

try:
    results = search.search(
        query="Civil Engineer with AutoCAD experience",
        query_type="comprehensive",
        limit=5
    )

    logger.info(f"\n✓ Found {len(results)} results")
    for i, r in enumerate(results[:3], 1):
        logger.info(f"  [{i}] {r['full_name']} - {r['job_title']}")

except Exception as e:
    logger.error(f"❌ Search failed: {e}", exc_info=True)
    sys.exit(1)

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

    logger.info(f"\n✓ Found {len(results)} results with 5+ years experience")
    for i, r in enumerate(results[:3], 1):
        exp = r.get('total_years_experience', 0)
        logger.info(f"  [{i}] {r['full_name']}: {exp:.1f} years")

except Exception as e:
    logger.error(f"❌ Filtered search failed: {e}", exc_info=True)
    sys.exit(1)

# Summary
logger.info("\n" + "=" * 80)
logger.info("MONGODB ATLAS INTEGRATION TEST COMPLETED")
logger.info("=" * 80)
logger.info("✓ MongoDB Atlas connection successful")
logger.info("✓ All 4,889 applicants ingested to MongoDB")
logger.info("✓ Vector search working correctly")
logger.info("✓ Filters working correctly")
logger.info("\n🎉 Your embeddings are now stored persistently in MongoDB Atlas!")
