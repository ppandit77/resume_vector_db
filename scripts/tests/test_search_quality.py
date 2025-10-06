"""
Search Quality Diagnostic Test
Tests search results and analyzes metadata usage
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.superlinked_production import ProductionSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("\n" + "=" * 80)
logger.info("SEARCH QUALITY DIAGNOSTIC TEST")
logger.info("=" * 80)

# Initialize search
logger.info("\n[1/3] Initializing search system...")
search = ProductionSearch(
    'data/processed/applicants_with_embeddings_clean.json',
    enable_natural_language=False,
    use_mongodb=False,
    use_qdrant=True,
    skip_ingestion=True
)

# Test query
test_query = "Civil Engineer with AutoCAD experience"
logger.info(f"\n[2/3] Testing query: '{test_query}'")

results = search.search(
    query=test_query,
    query_type="comprehensive",
    limit=10
)

logger.info(f"\n[3/3] Analyzing results...")
logger.info("=" * 80)

if len(results) == 0:
    logger.error("❌ No results found!")
else:
    logger.info(f"✅ Found {len(results)} results\n")

    for i, result in enumerate(results[:5], 1):
        logger.info(f"\n--- Result #{i} ---")
        logger.info(f"Name: {result.get('full_name', 'N/A')}")
        logger.info(f"Job Title: {result.get('job_title', 'N/A')}")
        logger.info(f"Experience: {result.get('total_years_experience', 0):.1f} years")
        logger.info(f"Location: {result.get('location', 'N/A')}")
        logger.info(f"Education: {result.get('highest_education_level', 'N/A')}")

        # Check if skills match query
        skills = result.get('skills_list', [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',')]

        # Look for AutoCAD or civil engineering related skills
        autocad_match = any('autocad' in str(s).lower() for s in skills)
        civil_match = any('civil' in str(s).lower() for s in skills)

        logger.info(f"Skills ({len(skills)} total):")
        if autocad_match:
            logger.info("  ✓ AutoCAD found in skills")
        else:
            logger.info("  ✗ No AutoCAD in skills")

        if civil_match:
            logger.info("  ✓ Civil engineering related skills found")
        else:
            logger.info("  ✗ No civil engineering skills found")

        # Show sample skills
        sample_skills = skills[:10] if isinstance(skills, list) else []
        logger.info(f"  Sample skills: {', '.join(sample_skills)}")

        # Check resume text for keywords
        resume_text = result.get('resume_full_text', '').lower()
        if 'autocad' in resume_text:
            logger.info("  ✓ AutoCAD mentioned in resume")
        if 'civil' in resume_text:
            logger.info("  ✓ Civil mentioned in resume")

logger.info("\n" + "=" * 80)
logger.info("DIAGNOSTIC COMPLETE")
logger.info("=" * 80)
