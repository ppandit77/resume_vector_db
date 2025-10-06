"""
Create payload indexes for filtering fields
Required for fast metadata filtering in Qdrant
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from core.load_env import load_env
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


COLLECTION_NAME = "applicants_unified"


def create_indexes():
    """Create payload indexes for filtering fields"""

    load_env()

    # Connect to Qdrant
    logger.info("\n" + "=" * 80)
    logger.info("CREATING PAYLOAD INDEXES")
    logger.info("=" * 80)

    url = os.getenv('QDRANT_URL')
    api_key = os.getenv('QDRANT_API_KEY')

    logger.info(f"\nConnecting to Qdrant Cloud...")
    logger.info(f"  URL: {url}")

    client = QdrantClient(url=url, api_key=api_key, timeout=120)

    # Create indexes for filtering fields
    logger.info(f"\nCreating indexes on collection '{COLLECTION_NAME}'...")

    indexes = [
        ("total_years_experience", PayloadSchemaType.FLOAT, "Enables experience range filtering"),
        ("longest_tenure_years", PayloadSchemaType.FLOAT, "Enables tenure range filtering"),
        ("location", PayloadSchemaType.KEYWORD, "Enables exact location matching"),
        ("education_level", PayloadSchemaType.KEYWORD, "Enables exact education matching"),
        ("current_stage", PayloadSchemaType.KEYWORD, "Enables application stage filtering"),
        ("date_applied", PayloadSchemaType.INTEGER, "Enables date range filtering (Unix timestamp)"),
        ("job_title", PayloadSchemaType.TEXT, "Enables fuzzy job title matching"),
        ("company_names", PayloadSchemaType.TEXT, "Enables fuzzy company name matching"),
    ]

    for field_name, field_type, description in indexes:
        try:
            logger.info(f"\n  Creating index: {field_name} ({field_type})")
            logger.info(f"    Purpose: {description}")

            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_type
            )

            logger.info(f"    ✓ Index created")

        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"    ✓ Index already exists (skipped)")
            else:
                logger.error(f"    ✗ Failed to create index: {e}")
                raise

    # Verify indexes
    logger.info(f"\nVerifying indexes...")
    collection_info = client.get_collection(COLLECTION_NAME)

    logger.info(f"  Collection status: {collection_info.status}")
    logger.info(f"  Total points: {collection_info.points_count}")

    logger.info("\n" + "=" * 80)
    logger.info("INDEXES CREATED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info("You can now filter by:")
    logger.info("  - total_years_experience (range queries)")
    logger.info("  - longest_tenure_years (range queries)")
    logger.info("  - location (exact match)")
    logger.info("  - education_level (exact match)")
    logger.info("  - current_stage (exact match)")
    logger.info("  - date_applied (range queries for recent applicants)")
    logger.info("  - job_title (fuzzy text match)")
    logger.info("  - company_names (fuzzy text match)")

    return True


if __name__ == "__main__":
    try:
        success = create_indexes()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)
