"""
Working Superlinked Integration for Applicant Search
Based on official v37.4.2 API
Using Pre-Generated Gemini Embeddings (3072-dim)
"""

import json
import logging
from datetime import timedelta
from typing import List, Dict, Any

import superlinked.framework as sl

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

class ApplicantSchema(sl.Schema):
    """
    Applicant schema matching our preprocessed data.
    Now includes pre-generated Gemini embeddings!
    """
    # ID field (required)
    id: sl.IdField

    # Contact & Display fields
    full_name: sl.String
    email: sl.String
    resume_url: sl.String

    # Core text fields (for search)
    job_title: sl.String
    skills_extracted: sl.String
    resume_full_text: sl.String
    tasks_summary: sl.String

    # Pre-generated Gemini embeddings (3072-dimensional)
    embedding_resume: sl.FloatList
    embedding_skills: sl.FloatList
    embedding_tasks: sl.FloatList

    # Work history fields
    current_company: sl.String
    company_names: sl.String  # For searching past companies
    work_history_text: sl.String

    # Location & Education
    location: sl.String
    education_level: sl.String
    current_stage: sl.String

    # Numeric fields
    total_years_experience: sl.Float
    longest_tenure_years: sl.Float

    # Temporal field
    date_applied: sl.Timestamp


# ============================================================================
# SETUP SPACES AND INDEX
# ============================================================================

def create_search_system():
    """
    Create complete Superlinked search system.
    """
    logger.info("=" * 80)
    logger.info("CREATING SUPERLINKED SEARCH SYSTEM")
    logger.info("=" * 80)

    # 1. Initialize schema
    logger.info("\n[1/6] Creating schema...")
    applicant = ApplicantSchema()

    # 2. Create spaces
    logger.info("\n[2/6] Creating vector spaces...")

    # Custom spaces using pre-generated Gemini embeddings (3072-dim)
    logger.info("  Using pre-generated Gemini embeddings (3072-dim)...")

    resume_space = sl.CustomSpace(
        vector=applicant.embedding_resume,
        length=3072
    )

    skills_space = sl.CustomSpace(
        vector=applicant.embedding_skills,
        length=3072
    )

    tasks_space = sl.CustomSpace(
        vector=applicant.embedding_tasks,
        length=3072
    )

    # Text similarity spaces for other fields (sentence-transformers)
    job_space = sl.TextSimilaritySpace(
        text=applicant.job_title,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    company_space = sl.TextSimilaritySpace(
        text=applicant.company_names,
        model="sentence-transformers/all-mpnet-base-v2"
    )

    # Number spaces
    experience_space = sl.NumberSpace(
        number=applicant.total_years_experience,
        min_value=0.0,
        max_value=50.0,
        mode=sl.Mode.MAXIMUM
    )

    tenure_space = sl.NumberSpace(
        number=applicant.longest_tenure_years,
        min_value=0.0,
        max_value=30.0,
        mode=sl.Mode.MAXIMUM
    )

    # Recency space
    recency_space = sl.RecencySpace(
        timestamp=applicant.date_applied,
        period_time_list=[
            sl.PeriodTime(timedelta(days=7)),
            sl.PeriodTime(timedelta(days=30)),
            sl.PeriodTime(timedelta(days=90)),
            sl.PeriodTime(timedelta(days=180))
        ]
    )

    # Categorical spaces
    education_space = sl.CategoricalSimilaritySpace(
        category_input=applicant.education_level,
        categories=[
            "Master's Degree",
            "Bachelor's Degree",
            "Associate's Degree",
            "Diploma/Vocational",
            "Doctorate",
            "Not Specified"
        ],
        negative_filter=-5.0
    )

    location_space = sl.CategoricalSimilaritySpace(
        category_input=applicant.location,
        categories=[
            "Manila, Philippines",
            "Quezon City, Philippines",
            "Davao City, Philippines",
            "Cebu City, Philippines",
            "Iloilo City, Philippines",
            "Unknown"
        ],
        negative_filter=-3.0
    )

    logger.info("  Created 10 spaces")

    # 3. Create index with all spaces
    logger.info("\n[3/6] Creating index...")
    index = sl.Index([
        job_space,
        skills_space,
        resume_space,
        tasks_space,
        company_space,
        experience_space,
        tenure_space,
        recency_space,
        education_space,
        location_space
    ])

    # 4. Create queries
    logger.info("\n[4/6] Creating queries...")

    # Comprehensive search query (using pre-generated embeddings)
    comprehensive_query = (
        sl.Query(
            index,
            weights={
                resume_space: sl.Param("resume_weight", default=0.4),
                skills_space: sl.Param("skills_weight", default=0.3),
                experience_space: sl.Param("exp_weight", default=0.15),
                recency_space: sl.Param("recency_weight", default=0.1),
                education_space: sl.Param("edu_weight", default=0.05)
            }
        )
        .find(applicant)
        .similar(resume_space.vector, sl.Param("query_vector"))
        .filter(applicant.total_years_experience >= sl.Param("min_exp", default=0.0))
        .limit(sl.Param("limit", default=20))
        .select_all()
    )

    # Skills-focused query
    skills_query = (
        sl.Query(
            index,
            weights={
                skills_space: 0.7,
                experience_space: 0.3
            }
        )
        .find(applicant)
        .similar(skills_space.vector, sl.Param("query_vector"))
        .filter(applicant.total_years_experience >= sl.Param("min_exp", default=0.0))
        .limit(sl.Param("limit", default=20))
        .select_all()
    )

    # Job title query
    job_query = (
        sl.Query(
            index,
            weights={
                job_space: 0.6,
                experience_space: 0.2,
                education_space: 0.2
            }
        )
        .find(applicant)
        .similar(job_space.text, sl.Param("query"))
        .limit(sl.Param("limit", default=20))
        .select_all()
    )

    # Recent applicants
    recent_query = (
        sl.Query(
            index,
            weights={
                recency_space: 0.5,
                resume_space: 0.5
            }
        )
        .find(applicant)
        .similar(resume_space.vector, sl.Param("query_vector"))
        .limit(sl.Param("limit", default=20))
        .select_all()
    )

    # Company search - find people who worked at specific companies
    company_query = (
        sl.Query(
            index,
            weights={
                company_space: 0.7,
                experience_space: 0.2,
                skills_space: 0.1
            }
        )
        .find(applicant)
        .similar(company_space.text, sl.Param("query"))
        .limit(sl.Param("limit", default=20))
        .select_all()
    )

    queries = {
        "comprehensive": comprehensive_query,
        "skills": skills_query,
        "job": job_query,
        "recent": recent_query,
        "company": company_query
    }

    logger.info(f"  Created {len(queries)} query types")

    # 5. Setup executor
    logger.info("\n[5/6] Setting up executor...")
    source = sl.InMemorySource(applicant)
    executor = sl.InMemoryExecutor(sources=[source], indices=[index])
    app = executor.run()

    logger.info("\n" + "=" * 80)
    logger.info("✅ SYSTEM CREATED")
    logger.info("=" * 80)

    return {
        "app": app,
        "source": source,
        "applicant": applicant,
        "queries": queries
    }


# ============================================================================
# QUERY EMBEDDING HELPER
# ============================================================================

def generate_query_embedding(query_text: str) -> List[float]:
    """
    Generate embedding for a query using Gemini.
    """
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from gemini_embedder_prod import GeminiEmbedder

    embedder = GeminiEmbedder()
    return embedder.embed_single(query_text)


# ============================================================================
# DATA LOADING AND INGESTION
# ============================================================================

def load_and_ingest_data(system: Dict, data_file: str):
    """
    Load applicant data and ingest into Superlinked.
    """
    logger.info("\n[6/6] Loading and ingesting data...")

    # Load data
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"  Loaded {len(data)} applicants")

    # Ingest in batches
    batch_size = 100
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        system["source"].put(batch)

        if (i + batch_size) % 500 == 0:
            logger.info(f"  Ingested {i + batch_size}/{len(data)} records...")

    logger.info(f"✓ Ingested {len(data)} applicants")
    return len(data)


# ============================================================================
# SEARCH INTERFACE
# ============================================================================

class SuperlinkedSearch:
    """
    User-friendly search interface.
    """

    def __init__(self, data_file: str):
        """Initialize search system with data."""
        self.system = create_search_system()
        self.total_records = load_and_ingest_data(self.system, data_file)

        # Initialize Gemini embedder for query embeddings
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from gemini_embedder_prod import GeminiEmbedder
        self.embedder = GeminiEmbedder()

        logger.info("\n" + "=" * 80)
        logger.info("🚀 SEARCH SYSTEM READY")
        logger.info("=" * 80)
        logger.info(f"Total applicants: {self.total_records}")

    def search(
        self,
        query: str,
        query_type: str = "comprehensive",
        min_experience: float = 0.0,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for applicants.

        Args:
            query: Search query text
            query_type: Query type to use
                - "comprehensive" (default): Full resume + skills + experience + education
                - "skills": Focus on skills match
                - "job": Job title search
                - "recent": Recent applicants
                - "company": Find people who worked at specific companies
            min_experience: Minimum years of experience
            limit: Number of results

        Returns:
            List of matching applicants with all fields including:
            - full_name, email, resume_url
            - job_title, current_company, company_names
            - skills_extracted, location, education_level
            - total_years_experience, longest_tenure_years
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"SEARCHING: '{query}'")
        logger.info(f"{'='*80}")
        logger.info(f"Type: {query_type}")
        logger.info(f"Min experience: {min_experience}")

        # Generate query embedding using Gemini
        logger.info("  Generating query embedding with Gemini...")
        query_vector = self.embedder.embed_single(query)

        # Get query
        query_obj = self.system["queries"].get(query_type, self.system["queries"]["comprehensive"])

        # Execute with query vector
        result = self.system["app"].query(
            query_obj,
            query_vector=query_vector,
            min_exp=min_experience,
            limit=limit
        )

        # Convert to pandas for easier handling
        df = sl.PandasConverter.to_pandas(result)

        logger.info(f"✓ Found {len(df)} results")

        # Convert to list of dicts
        return df.to_dict('records')

    def format_results(self, results: List[Dict]) -> str:
        """Format results for display."""
        if not results:
            return "No results found."

        output = []
        output.append(f"\nFound {len(results)} results:\n")
        output.append("=" * 80)

        for i, result in enumerate(results, 1):
            output.append(f"\n[{i}]")
            output.append(f"  Name: {result.get('full_name', 'N/A')}")
            output.append(f"  Email: {result.get('email', 'N/A')}")
            output.append(f"  Job: {result.get('job_title', 'N/A')}")
            output.append(f"  Current Company: {result.get('current_company', 'N/A')}")
            output.append(f"  Location: {result.get('location', 'Unknown')}")
            output.append(f"  Experience: {result.get('total_years_experience', 0):.1f} years")
            output.append(f"  Education: {result.get('education_level', 'N/A')}")

            skills = result.get('skills_extracted', '')
            if skills:
                output.append(f"  Skills: {skills[:100]}{'...' if len(skills) > 100 else ''}")

            companies = result.get('company_names', '')
            if companies:
                output.append(f"  Past Companies: {companies[:100]}{'...' if len(companies) > 100 else ''}")

            resume_url = result.get('resume_url', '')
            if resume_url:
                output.append(f"  Resume: {resume_url}")

        output.append("\n" + "=" * 80)
        return "\n".join(output)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example usage"""

    # File path - using data with pre-generated Gemini embeddings
    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json"

    # Initialize
    logger.info("Initializing Superlinked search with Gemini embeddings...")
    search = SuperlinkedSearch(DATA_FILE)

    # Example 1: Comprehensive search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 1: Search for Senior Engineers")
    logger.info("=" * 80)

    results = search.search(
        query="Senior Civil Engineer with structural design and AutoCAD experience",
        query_type="comprehensive",
        min_experience=5,
        limit=5
    )

    print(search.format_results(results))

    # Example 2: Skills search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 2: Search for AutoCAD skills")
    logger.info("=" * 80)

    results = search.search(
        query="AutoCAD Revit SketchUp 3D modeling",
        query_type="skills",
        min_experience=3,
        limit=5
    )

    print(search.format_results(results))

    # Example 3: Job title search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 3: Search for Project Managers")
    logger.info("=" * 80)

    results = search.search(
        query="Project Manager",
        query_type="job",
        limit=5
    )

    print(search.format_results(results))

    # Example 4: Company search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 4: Find people who worked at National Housing Authority")
    logger.info("=" * 80)

    results = search.search(
        query="National Housing Authority",
        query_type="company",
        limit=5
    )

    print(search.format_results(results))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠ Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
