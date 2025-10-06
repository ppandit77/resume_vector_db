"""
Delete old Qdrant collections before migration
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from qdrant_client import QdrantClient
from core.load_env import load_env
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def delete_old_collections():
    """Delete all existing Qdrant collections"""

    load_env()

    # Connect to Qdrant
    logger.info("\n" + "=" * 80)
    logger.info("DELETING OLD QDRANT COLLECTIONS")
    logger.info("=" * 80)

    url = os.getenv('QDRANT_URL')
    api_key = os.getenv('QDRANT_API_KEY')

    logger.info(f"\nConnecting to Qdrant Cloud...")
    logger.info(f"  URL: {url}")

    client = QdrantClient(url=url, api_key=api_key, timeout=60)

    # List all collections
    logger.info(f"\nListing current collections...")
    collections = client.get_collections()

    if not collections.collections:
        logger.info("  No collections found. Already clean!")
        return

    logger.info(f"  Found {len(collections.collections)} collections:")
    for col in collections.collections:
        info = client.get_collection(col.name)
        logger.info(f"    - '{col.name}' ({info.points_count} points)")

    # Confirm deletion
    logger.info(f"\n⚠️  WARNING: This will delete ALL collections!")
    response = input("\nType 'DELETE' to confirm: ")

    if response != "DELETE":
        logger.info("Aborted. No collections deleted.")
        return

    # Delete each collection
    logger.info(f"\nDeleting collections...")
    for col in collections.collections:
        try:
            client.delete_collection(col.name)
            logger.info(f"  ✓ Deleted '{col.name}'")
        except Exception as e:
            logger.error(f"  ✗ Failed to delete '{col.name}': {e}")

    # Verify deletion
    logger.info(f"\nVerifying deletion...")
    collections_after = client.get_collections()

    if not collections_after.collections:
        logger.info("  ✓ All collections deleted successfully!")
    else:
        logger.warning(f"  ⚠️  {len(collections_after.collections)} collections still remain:")
        for col in collections_after.collections:
            logger.warning(f"    - {col.name}")

    logger.info("\n" + "=" * 80)
    logger.info("CLEANUP COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        delete_old_collections()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)
