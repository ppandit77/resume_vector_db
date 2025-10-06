"""
Quick test to show what query results look like
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
    resume_url: sl.String
    job_title: sl.String
    skills_extracted: sl.String
    resume_full_text: sl.String
    tasks_summary: sl.String
    current_company: sl.String
    company_names: sl.String
    work_history_text: sl.String
    location: sl.String
    education_level: sl.String
    current_stage: sl.String
    total_years_experience: sl.Float
    longest_tenure_years: sl.Float
    date_applied: sl.Timestamp


def main():
    logger.info("Creating search system...")

    # Schema
    applicant = ApplicantSchema()

    # Minimal spaces for testing
    resume_space = sl.TextSimilaritySpace(
        text=applicant.resume_full_text,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    skills_space = sl.TextSimilaritySpace(
        text=applicant.skills_extracted,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    company_space = sl.TextSimilaritySpace(
        text=applicant.company_names,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    # Index
    index = sl.Index([resume_space, skills_space, company_space])

    # Query
    query = (
        sl.Query(
            index,
            weights={
                resume_space: 0.5,
                skills_space: 0.3,
                company_space: 0.2
            }
        )
        .find(applicant)
        .similar(resume_space.text, sl.Param("query"))
        .limit(sl.Param("limit", default=3))
        .select_all()
    )

    # Executor
    source = sl.InMemorySource(applicant)
    executor = sl.InMemoryExecutor(sources=[source], indices=[index])
    app = executor.run()

    # Load 20 records
    logger.info("Loading 20 records...")
    with open("/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/preprocessed_with_gpt_batch.json", 'r') as f:
        data = json.load(f)[:20]

    source.put(data)
    logger.info("✓ Data ingested")

    # Search
    logger.info("\n" + "=" * 80)
    logger.info("SEARCH: Civil Engineer with AutoCAD")
    logger.info("=" * 80)

    result = app.query(query, query="Civil Engineer with AutoCAD experience", limit=3)
    df = sl.PandasConverter.to_pandas(result)

    print("\n" + "=" * 80)
    print("QUERY RESULTS - ALL AVAILABLE FIELDS")
    print("=" * 80)

    for i, row in df.iterrows():
        print(f"\n[Result {i+1}]")
        print(f"  Name: {row.get('full_name', 'N/A')}")
        print(f"  Email: {row.get('email', 'N/A')}")
        print(f"  Job Title: {row.get('job_title', 'N/A')}")
        print(f"  Current Company: {row.get('current_company', 'N/A')}")
        print(f"  Location: {row.get('location', 'N/A')}")
        print(f"  Total Experience: {row.get('total_years_experience', 0):.1f} years")
        print(f"  Longest Tenure: {row.get('longest_tenure_years', 0):.1f} years")
        print(f"  Education: {row.get('education_level', 'N/A')}")
        print(f"  Current Stage: {row.get('current_stage', 'N/A')}")

        skills = row.get('skills_extracted', '')
        print(f"  Skills: {skills[:120]}{'...' if len(skills) > 120 else ''}")

        companies = row.get('company_names', '')
        print(f"  Past Companies: {companies[:120]}{'...' if len(companies) > 120 else ''}")

        tasks = row.get('tasks_summary', '')
        print(f"  Tasks: {tasks[:150]}{'...' if len(tasks) > 150 else ''}")

        resume_url = row.get('resume_url', '')
        print(f"  Resume URL: {resume_url}")

    print("\n" + "=" * 80)
    logger.info("✅ Test completed")


if __name__ == "__main__":
    main()
