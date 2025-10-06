"""
Test Enhanced Filters in Production Search System
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent scripts directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_filters():
    """Test all new filter capabilities"""

    # Data file
    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json"

    logger.info("\n" + "=" * 80)
    logger.info("TESTING ENHANCED FILTERS")
    logger.info("=" * 80)

    # Initialize search system
    logger.info("\n[1/6] Initializing search system (this may take a few minutes)...")
    search = ProductionSearch(DATA_FILE, enable_natural_language=False)

    # Test 1: Basic search (no filters)
    logger.info("\n" + "=" * 80)
    logger.info("[2/6] TEST 1: Basic Search - No Filters")
    logger.info("=" * 80)

    results = search.search(
        query="Civil Engineer with AutoCAD",
        query_type="comprehensive",
        limit=5
    )

    logger.info(f"✓ Found {len(results)} results without filters")
    if results:
        logger.info(f"  Sample: {results[0]['full_name']} - {results[0]['job_title']}")

    # Test 2: Experience filter
    logger.info("\n" + "=" * 80)
    logger.info("[3/6] TEST 2: Experience Filter - Min 5 years")
    logger.info("=" * 80)

    results = search.search(
        query="Civil Engineer with AutoCAD",
        query_type="comprehensive",
        min_experience=5.0,
        limit=5
    )

    logger.info(f"✓ Found {len(results)} results with min_experience=5.0")
    if results:
        for i, r in enumerate(results[:3], 1):
            exp = r.get('total_years_experience', 0)
            logger.info(f"  [{i}] {r['full_name']}: {exp:.1f} years experience")
            if exp < 5.0:
                logger.error(f"    ❌ FILTER FAILED: {exp} < 5.0")

    # Test 3: Education filter
    logger.info("\n" + "=" * 80)
    logger.info("[4/6] TEST 3: Education Filter - Bachelor's Degree")
    logger.info("=" * 80)

    results = search.search(
        query="Engineer",
        query_type="comprehensive",
        education_level="Bachelor's Degree",
        limit=5
    )

    logger.info(f"✓ Found {len(results)} results with education_level='Bachelor's Degree'")
    if results:
        for i, r in enumerate(results[:3], 1):
            edu = r.get('education_level', 'N/A')
            logger.info(f"  [{i}] {r['full_name']}: {edu}")
            if edu != "Bachelor's Degree":
                logger.error(f"    ❌ FILTER FAILED: {edu} != Bachelor's Degree")

    # Test 4: Location filter
    logger.info("\n" + "=" * 80)
    logger.info("[5/6] TEST 4: Location Filter - Manila/Davao")
    logger.info("=" * 80)

    # First try Manila
    results_manila = search.search(
        query="Engineer",
        query_type="comprehensive",
        location="Manila, Philippines",
        limit=5
    )

    logger.info(f"✓ Manila results: {len(results_manila)}")
    if results_manila:
        for i, r in enumerate(results_manila[:2], 1):
            loc = r.get('location', 'N/A')
            logger.info(f"  [{i}] {r['full_name']}: {loc}")

    # Test 5: Multiple filters combined
    logger.info("\n" + "=" * 80)
    logger.info("[6/6] TEST 5: Multiple Filters Combined")
    logger.info("=" * 80)

    results = search.search(
        query="Engineer with AutoCAD",
        query_type="comprehensive",
        min_experience=3.0,
        min_tenure=1.0,
        education_level="Bachelor's Degree",
        limit=5
    )

    logger.info(f"✓ Found {len(results)} results with multiple filters:")
    logger.info(f"  - min_experience: 3.0")
    logger.info(f"  - min_tenure: 1.0")
    logger.info(f"  - education_level: Bachelor's Degree")

    if results:
        for i, r in enumerate(results[:3], 1):
            exp = r.get('total_years_experience', 0)
            tenure = r.get('longest_tenure_years', 0)
            edu = r.get('education_level', 'N/A')
            logger.info(f"  [{i}] {r['full_name']}")
            logger.info(f"      Experience: {exp:.1f} years")
            logger.info(f"      Tenure: {tenure:.1f} years")
            logger.info(f"      Education: {edu}")

            # Validate
            if exp < 3.0:
                logger.error(f"      ❌ Experience filter failed: {exp} < 3.0")
            if tenure < 1.0:
                logger.error(f"      ❌ Tenure filter failed: {tenure} < 1.0")
            if edu != "Bachelor's Degree":
                logger.error(f"      ❌ Education filter failed: {edu}")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("FILTER TESTING COMPLETED")
    logger.info("=" * 80)
    logger.info("✓ All filter tests executed successfully")
    logger.info("Review the logs above to verify filter behavior")


if __name__ == "__main__":
    try:
        test_filters()
    except KeyboardInterrupt:
        logger.info("\n⚠ Testing interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error during testing: {e}", exc_info=True)
