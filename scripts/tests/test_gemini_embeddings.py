"""
Test Superlinked with Pre-Generated Gemini Embeddings
Quick test with 20 records
"""

import json
import logging
from datetime import timedelta
import superlinked.framework as sl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApplicantSchema(sl.Schema):
    id: sl.IdField
    full_name: sl.String
    email: sl.String
    job_title: sl.String
    current_company: sl.String
    location: sl.String
    total_years_experience: sl.Float
    education_level: sl.String
    skills_extracted: sl.String
    date_applied: sl.Timestamp

    # Pre-generated Gemini embeddings
    embedding_resume: sl.FloatList
    embedding_skills: sl.FloatList
    embedding_tasks: sl.FloatList


def main():
    logger.info("=" * 80)
    logger.info("TESTING WITH GEMINI EMBEDDINGS (20 RECORDS)")
    logger.info("=" * 80)

    # Schema
    applicant = ApplicantSchema()

    # Custom spaces using Gemini embeddings
    logger.info("\n[1/4] Creating spaces with Gemini embeddings (3072-dim)...")

    resume_space = sl.CustomSpace(
        vector=applicant.embedding_resume,
        length=3072
    )

    skills_space = sl.CustomSpace(
        vector=applicant.embedding_skills,
        length=3072
    )

    logger.info("  ✓ Created custom spaces")

    # Index
    logger.info("\n[2/4] Creating index...")
    index = sl.Index([resume_space, skills_space])

    # Query
    logger.info("\n[3/4] Creating query...")
    query = (
        sl.Query(
            index,
            weights={
                resume_space: 0.6,
                skills_space: 0.4
            }
        )
        .find(applicant)
        .similar(resume_space.vector, sl.Param("query_vector"))
        .limit(sl.Param("limit", default=5))
        .select_all()
    )

    # Executor
    source = sl.InMemorySource(applicant)
    executor = sl.InMemoryExecutor(sources=[source], indices=[index])
    app = executor.run()

    # Load 20 records WITH EMBEDDINGS
    logger.info("\n[4/4] Loading 20 records with embeddings...")
    with open("/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json", 'r') as f:
        data = json.load(f)[:20]

    logger.info(f"  Loaded {len(data)} records")

    # Verify embeddings exist
    sample = data[0]
    logger.info(f"  ✓ Sample has embedding_resume: {len(sample['embedding_resume'])} dims")
    logger.info(f"  ✓ Sample has embedding_skills: {len(sample['embedding_skills'])} dims")

    # Ingest
    logger.info("\n  Ingesting...")
    source.put(data)
    logger.info("  ✓ Ingested")

    # Generate query embedding
    logger.info("\n" + "=" * 80)
    logger.info("SEARCH TEST: Civil Engineer with AutoCAD")
    logger.info("=" * 80)

    import sys
    import os
    # Add parent scripts directory to path
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.gemini_embedder_prod import GeminiEmbedder

    embedder = GeminiEmbedder()
    query_text = "Civil Engineer with AutoCAD experience"

    logger.info(f"  Generating query embedding...")
    query_vector = embedder.embed_single(query_text)
    logger.info(f"  ✓ Query embedding: {len(query_vector)} dims")

    # Search
    result = app.query(query, query_vector=query_vector, limit=3)
    df = sl.PandasConverter.to_pandas(result)

    print("\n" + "=" * 80)
    print("SEARCH RESULTS")
    print("=" * 80)

    for i, row in df.iterrows():
        print(f"\n[{i+1}]")
        print(f"  Name: {row.get('full_name', 'N/A')}")
        print(f"  Email: {row.get('email', 'N/A')}")
        print(f"  Job: {row.get('job_title', 'N/A')}")
        print(f"  Company: {row.get('current_company', 'N/A')}")
        print(f"  Location: {row.get('location', 'N/A')}")
        print(f"  Experience: {row.get('total_years_experience', 0):.1f} years")
        skills = row.get('skills_extracted', '')[:100]
        print(f"  Skills: {skills}...")

    print("\n" + "=" * 80)
    logger.info("✅ TEST COMPLETED - Gemini embeddings working!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
