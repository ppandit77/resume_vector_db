"""
Superlinked Minimal Test (10 records only)
Very quick test version
"""

import json
import logging
from datetime import timedelta
from typing import List, Dict

import superlinked.framework as sl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApplicantSchema(sl.Schema):
    id: sl.IdField
    full_name: sl.String
    job_title: sl.String
    skills_extracted: sl.String
    resume_full_text: sl.String
    total_years_experience: sl.Float
    location: sl.String
    education_level: sl.String
    date_applied: sl.Timestamp


def main():
    logger.info("=" * 80)
    logger.info("MINIMAL TEST - 10 RECORDS")
    logger.info("=" * 80)

    # 1. Schema
    logger.info("\n[1/4] Creating schema...")
    applicant = ApplicantSchema()

    # 2. Spaces (minimal set)
    logger.info("\n[2/4] Creating spaces...")

    resume_space = sl.TextSimilaritySpace(
        text=applicant.resume_full_text,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    skills_space = sl.TextSimilaritySpace(
        text=applicant.skills_extracted,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    experience_space = sl.NumberSpace(
        number=applicant.total_years_experience,
        min_value=0.0,
        max_value=50.0,
        mode=sl.Mode.MAXIMUM
    )

    logger.info("  Created 3 spaces")

    # 3. Index
    logger.info("\n[3/4] Creating index...")
    index = sl.Index([resume_space, skills_space, experience_space])

    # 4. Query
    logger.info("\n[4/4] Creating query...")
    query = (
        sl.Query(
            index,
            weights={
                resume_space: 0.6,
                skills_space: 0.3,
                experience_space: 0.1
            }
        )
        .find(applicant)
        .similar(resume_space.text, sl.Param("query"))
        .limit(sl.Param("limit", default=5))
        .select_all()
    )

    # 5. Executor
    logger.info("\nSetting up executor...")
    source = sl.InMemorySource(applicant)
    executor = sl.InMemoryExecutor(sources=[source], indices=[index])
    app = executor.run()

    # 6. Load ONLY 10 records
    logger.info("\nLoading 10 records...")
    with open("/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/preprocessed_with_gpt_batch.json", 'r') as f:
        data = json.load(f)[:10]

    logger.info(f"  Loaded {len(data)} applicants")

    # 7. Ingest
    logger.info("\nIngesting...")
    source.put(data)
    logger.info("✓ Ingested")

    # 8. Search
    logger.info("\n" + "=" * 80)
    logger.info("TEST SEARCH: Civil Engineer")
    logger.info("=" * 80)

    result = app.query(
        query,
        query="Civil Engineer with AutoCAD experience",
        limit=5
    )

    df = sl.PandasConverter.to_pandas(result)

    logger.info(f"\n✓ Found {len(df)} results")

    print("\nResults:")
    print("=" * 80)
    for i, row in df.iterrows():
        print(f"\n[{i+1}] {row.get('full_name', 'N/A')}")
        print(f"    Job: {row.get('job_title', 'N/A')}")
        print(f"    Experience: {row.get('total_years_experience', 0):.1f} years")
        skills = row.get('skills_extracted', '')[:80]
        print(f"    Skills: {skills}...")

    print("\n" + "=" * 80)
    logger.info("✅ TEST COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
