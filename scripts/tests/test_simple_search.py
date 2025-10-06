"""
Test Simple Qdrant Search System
Upload data and test multi-embedding search
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.simple_qdrant_search import SimpleQdrantSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("SIMPLE QDRANT SEARCH TEST")
logger.info("=" * 80)

# Initialize
logger.info("\n[1/4] Initializing search system...")
search = SimpleQdrantSearch('data/processed/applicants_with_embeddings_clean.json')

# Create collections
logger.info("\n[2/4] Creating collections...")
search.create_collections()

# Upload data
logger.info("\n[3/4] Uploading data...")
search.upload_data(batch_size=50)

# Test search
logger.info("\n[4/4] Testing search...")
logger.info("=" * 80)

test_queries = [
    ("Civil Engineer with AutoCAD experience", {}),
    ("Python developer with machine learning", {"min_experience": 3.0}),
    ("Senior software engineer", {"min_experience": 5.0}),
]

for query, filters in test_queries:
    logger.info(f"\nQuery: '{query}'")
    if filters:
        logger.info(f"Filters: {filters}")

    results = search.search(query, limit=5, **filters)

    logger.info(f"\n✓ Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        logger.info(f"\n  {i}. {result['full_name']} - {result['job_title']}")
        logger.info(f"     Score: {result['score']:.3f} (sources: {', '.join(result['sources'])})")
        logger.info(f"     Experience: {result['total_years_experience']:.1f} years")
        logger.info(f"     Location: {result.get('location', 'N/A')}")

logger.info("\n" + "=" * 80)
logger.info("TEST COMPLETE")
logger.info("=" * 80)
