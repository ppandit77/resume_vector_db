"""
Network Timeout Test - Europe Cluster
Tests if queries timeout due to network latency
"""
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("\n" + "=" * 80)
logger.info("NETWORK TIMEOUT TEST - EUROPE CLUSTER")
logger.info("=" * 80)

# Connect to existing data
logger.info("\n[1/3] Connecting to Europe cluster (skip ingestion)...")
start_time = time.time()
try:
    search = ProductionSearch(
        'data/processed/applicants_with_embeddings_clean.json',
        enable_natural_language=False,
        use_mongodb=False,
        use_qdrant=True,
        skip_ingestion=True
    )
    connect_time = time.time() - start_time
    logger.info(f"✓ Connection successful ({connect_time:.2f}s)")
except Exception as e:
    logger.error(f"❌ Connection failed: {e}")
    sys.exit(1)

# Test search without filters (to avoid indexing errors)
logger.info("\n[2/3] Testing search query (no filters)...")
start_time = time.time()
try:
    # Don't pass min_experience to avoid filter indexing error
    results = search.search(
        query="Civil Engineer",
        query_type="comprehensive",
        limit=5
    )
    query_time = time.time() - start_time
    logger.info(f"✓ Query successful ({query_time:.2f}s)")
    logger.info(f"  Found {len(results)} results")

    if len(results) > 0:
        logger.info(f"  Sample: {results[0].get('full_name', 'N/A')} - {results[0].get('job_title', 'N/A')}")
except Exception as e:
    query_time = time.time() - start_time
    logger.error(f"❌ Query failed after {query_time:.2f}s: {e}")
    sys.exit(1)

# Summary
logger.info("\n" + "=" * 80)
logger.info("NETWORK TIMEOUT TEST RESULTS")
logger.info("=" * 80)
logger.info(f"✓ Connection time: {connect_time:.2f}s")
logger.info(f"✓ Query time: {query_time:.2f}s")

if query_time < 10:
    logger.info("\n🎉 NO TIMEOUT ISSUES - Europe cluster works great!")
elif query_time < 30:
    logger.info("\n⚠ Queries are a bit slow but acceptable")
else:
    logger.info("\n❌ Queries are very slow - may need optimization")

logger.info("=" * 80)
