"""
Create unified Qdrant collection with 3 named vectors and upload data
"""
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from core.load_env import load_env
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


COLLECTION_NAME = "applicants_unified"
DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings_clean.json"


def create_unified_collection():
    """Create single Qdrant collection with 3 named vectors"""

    load_env()

    # Connect to Qdrant
    logger.info("\n" + "=" * 80)
    logger.info("CREATING UNIFIED QDRANT COLLECTION")
    logger.info("=" * 80)

    url = os.getenv('QDRANT_URL')
    api_key = os.getenv('QDRANT_API_KEY')

    logger.info(f"\nConnecting to Qdrant Cloud...")
    logger.info(f"  URL: {url}")

    client = QdrantClient(url=url, api_key=api_key, timeout=120)

    # Delete collection if it already exists
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"\n  Deleted existing '{COLLECTION_NAME}' collection")
    except:
        pass

    # Create collection with 3 named vectors
    logger.info(f"\nCreating collection: '{COLLECTION_NAME}'")
    logger.info(f"  Configuration:")
    logger.info(f"    - resume vector: 3072 dimensions, COSINE distance")
    logger.info(f"    - skills vector: 3072 dimensions, COSINE distance")
    logger.info(f"    - tasks vector: 3072 dimensions, COSINE distance")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "resume": VectorParams(size=3072, distance=Distance.COSINE),
            "skills": VectorParams(size=3072, distance=Distance.COSINE),
            "tasks": VectorParams(size=3072, distance=Distance.COSINE)
        }
    )

    logger.info(f"  ✓ Collection created successfully!")

    # Verify collection
    collection_info = client.get_collection(COLLECTION_NAME)
    logger.info(f"\nCollection info:")
    logger.info(f"  Name: {collection_info.config.params}")
    logger.info(f"  Status: {collection_info.status}")
    logger.info(f"  Vectors: {collection_info.config.params.vectors}")

    return client


def upload_data(client: QdrantClient, batch_size: int = 50):
    """Upload applicant data with 3 vectors per point"""

    logger.info("\n" + "=" * 80)
    logger.info("UPLOADING DATA TO UNIFIED COLLECTION")
    logger.info("=" * 80)

    # Load data
    logger.info(f"\nLoading data from: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    logger.info(f"  ✓ Loaded {total} applicants")

    # Upload in batches
    logger.info(f"\nUploading {total} applicants in batches of {batch_size}...")

    points = []
    uploaded = 0
    skipped = 0

    for i, applicant in enumerate(data):
        # Validate embeddings
        resume_emb = applicant.get("embedding_resume", [])
        skills_emb = applicant.get("embedding_skills", [])
        tasks_emb = applicant.get("embedding_tasks", [])

        if len(resume_emb) != 3072 or len(skills_emb) != 3072 or len(tasks_emb) != 3072:
            logger.warning(f"  ⚠️  Skipping applicant {i}: invalid embedding dimensions")
            skipped += 1
            continue

        # Prepare payload (metadata)
        payload = {
            "id": applicant.get("id"),
            "full_name": applicant.get("full_name"),
            "email": applicant.get("email"),
            "job_title": applicant.get("job_title"),
            "current_stage": applicant.get("current_stage"),
            "education_level": applicant.get("education_level"),
            "total_years_experience": float(applicant.get("total_years_experience", 0)),
            "longest_tenure_years": float(applicant.get("longest_tenure_years", 0)),
            "current_company": applicant.get("current_company"),
            "location": applicant.get("location"),
            "skills_extracted": applicant.get("skills_extracted"),
            "tasks_summary": applicant.get("tasks_summary"),
            "resume_full_text": applicant.get("resume_full_text"),
            "resume_url": applicant.get("resume_url"),
            "date_applied": applicant.get("date_applied"),
            "company_names": applicant.get("company_names", ""),
            "work_history_text": applicant.get("work_history_text", "")
        }

        # Create point with 3 named vectors
        point = PointStruct(
            id=i,
            vector={
                "resume": resume_emb,
                "skills": skills_emb,
                "tasks": tasks_emb
            },
            payload=payload
        )

        points.append(point)

        # Upload batch
        if len(points) >= batch_size:
            try:
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points
                )
                uploaded += len(points)
                logger.info(f"  ✓ Uploaded batch: {uploaded}/{total} applicants")
                points = []
            except Exception as e:
                logger.error(f"  ✗ Batch upload failed: {e}")
                raise

    # Upload remaining points
    if points:
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            uploaded += len(points)
            logger.info(f"  ✓ Uploaded final batch: {uploaded}/{total} applicants")
        except Exception as e:
            logger.error(f"  ✗ Final batch upload failed: {e}")
            raise

    # Verify upload
    logger.info(f"\nVerifying upload...")
    count = client.count(COLLECTION_NAME).count
    logger.info(f"  ✓ Total points in collection: {count}")

    if skipped > 0:
        logger.warning(f"  ⚠️  Skipped {skipped} applicants due to invalid embeddings")

    logger.info("\n" + "=" * 80)
    logger.info("UPLOAD COMPLETE")
    logger.info("=" * 80)
    logger.info(f"  Collection: {COLLECTION_NAME}")
    logger.info(f"  Total applicants: {count}")
    logger.info(f"  Vectors per applicant: 3 (resume, skills, tasks)")
    logger.info(f"  Vector dimensions: 3072 (Gemini)")

    return count


def main():
    """Create collection and upload data"""

    # Create collection
    client = create_unified_collection()

    # Upload data
    count = upload_data(client)

    logger.info(f"\n🎉 SUCCESS! {count} applicants ready for intelligent search!")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)
