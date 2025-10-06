"""
Superlinked Integration with Pre-Generated Gemini Embeddings
Production-ready applicant search system
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add scripts to path
sys.path.append(os.path.dirname(__file__))

# Superlinked imports
from superlinked.framework.dsl.space.text_similarity_space import TextSimilaritySpace
from superlinked.framework.dsl.space.number_space import NumberSpace
from superlinked.framework.dsl.space.recency_space import RecencySpace
from superlinked.framework.dsl.space.categorical_similarity_space import CategoricalSimilaritySpace
from superlinked.framework.dsl.index.index import Index
from superlinked.framework.dsl.query.query import Query
from superlinked.framework.dsl.query.param import Param
from superlinked.framework.dsl.executor.in_memory.in_memory_executor import InMemoryExecutor
from superlinked.framework.dsl.source.in_memory_source import InMemorySource
from superlinked.framework.common.schema.schema import schema
from superlinked.framework.common.schema.schema_object import String, Integer, Float
from superlinked.framework.common.schema.id_schema_object import IdField
from superlinked.framework.dsl.space.number_space import Mode

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

@schema
class Applicant:
    """
    Superlinked schema for applicant data.
    Matches our preprocessed data structure.
    """
    # ID
    id: IdField

    # Core fields
    full_name: String
    email: String
    job_title: String
    current_stage: String

    # Education
    education_level: String
    location: String

    # Experience (numeric)
    total_years_experience: Float
    longest_tenure_years: Float

    # Text fields for embedding
    skills_extracted: String
    resume_full_text: String
    tasks_summary: String

    # Temporal
    date_applied: Integer  # Unix timestamp


# ============================================================================
# VECTOR SPACES SETUP
# ============================================================================

def create_spaces(applicant: Applicant) -> Dict[str, Any]:
    """
    Create all vector spaces for the applicant search system.

    Uses sentence-transformers for text fields since we're using
    pre-generated Gemini embeddings stored separately.
    """
    spaces = {
        # Text similarity spaces
        "job_title": TextSimilaritySpace(
            text=applicant.job_title,
            model="sentence-transformers/all-mpnet-base-v2"
        ),

        "skills": TextSimilaritySpace(
            text=applicant.skills_extracted,
            model="sentence-transformers/all-mpnet-base-v2"
        ),

        "resume": TextSimilaritySpace(
            text=applicant.resume_full_text,
            model="sentence-transformers/all-mpnet-base-v2"
        ),

        "tasks": TextSimilaritySpace(
            text=applicant.tasks_summary,
            model="sentence-transformers/all-mpnet-base-v2"
        ),

        # Numeric spaces
        "experience": NumberSpace(
            number=applicant.total_years_experience,
            min_value=0.0,
            max_value=50.0,
            mode=Mode.MAXIMUM
        ),

        "tenure": NumberSpace(
            number=applicant.longest_tenure_years,
            min_value=0.0,
            max_value=30.0,
            mode=Mode.MAXIMUM
        ),

        # Recency space
        "recency": RecencySpace(
            timestamp=applicant.date_applied,
            period_time_list=[
                timedelta(days=7),
                timedelta(days=30),
                timedelta(days=90),
                timedelta(days=180)
            ]
        ),

        # Categorical spaces
        "education": CategoricalSimilaritySpace(
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
        ),

        "location": CategoricalSimilaritySpace(
            category_input=applicant.location,
            categories=[
                "Manila", "Quezon City", "Davao", "Cebu",
                "Iloilo", "Batangas", "Makati", "Taguig",
                "Unknown"
            ],
            negative_filter=-3.0
        )
    }

    return spaces


# ============================================================================
# QUERIES
# ============================================================================

def create_queries(index: Index, applicant: Applicant, spaces: Dict) -> Dict:
    """Create search queries"""

    queries = {
        # Comprehensive search
        "comprehensive": (
            Query(index)
            .find(applicant)
            .similar(spaces["resume"], Param("query"))
            .filter(
                (applicant.total_years_experience >= Param("min_exp")) &
                (applicant.current_stage == Param("stage"))
            )
            .with_vector(spaces["skills"], weight=0.3)
            .with_vector(spaces["experience"], weight=0.2)
            .with_vector(spaces["education"], weight=0.1)
            .with_vector(spaces["recency"], weight=0.1)
            .limit(Param("limit"))
        ),

        # Skills-focused search
        "skills_search": (
            Query(index)
            .find(applicant)
            .similar(spaces["skills"], Param("query"))
            .filter(applicant.total_years_experience >= Param("min_exp"))
            .with_vector(spaces["experience"], weight=0.3)
            .limit(Param("limit"))
        ),

        # Job title search
        "job_search": (
            Query(index)
            .find(applicant)
            .similar(spaces["job_title"], Param("query"))
            .filter(applicant.education_level == Param("education"))
            .with_vector(spaces["experience"], weight=0.2)
            .limit(Param("limit"))
        ),

        # Recent applicants
        "recent": (
            Query(index)
            .find(applicant)
            .similar(spaces["resume"], Param("query"))
            .with_vector(spaces["recency"], weight=0.5)
            .limit(Param("limit"))
        )
    }

    return queries


# ============================================================================
# DATA LOADING
# ============================================================================

def load_applicant_data(json_file: str) -> List[Dict[str, Any]]:
    """Load preprocessed applicant data"""
    logger.info(f"Loading applicants from {json_file}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"✓ Loaded {len(data)} applicants")
    return data


# ============================================================================
# MAIN SYSTEM
# ============================================================================

class SuperlinkedApplicantSearch:
    """
    Production-ready applicant search system using Superlinked.
    """

    def __init__(self, data_file: str):
        """
        Initialize the search system.

        Args:
            data_file: Path to preprocessed JSON data
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING SUPERLINKED SEARCH SYSTEM")
        logger.info("=" * 80)

        # Load data
        logger.info("\n[1/5] Loading applicant data...")
        self.data = load_applicant_data(data_file)

        # Create schema
        logger.info("\n[2/5] Creating schema...")
        self.applicant = Applicant()

        # Create spaces
        logger.info("\n[3/5] Creating vector spaces...")
        self.spaces = create_spaces(self.applicant)
        logger.info(f"  Created {len(self.spaces)} spaces")

        # Create index
        logger.info("\n[4/5] Building index...")
        self.index = Index(list(self.spaces.values()))

        # Create queries
        logger.info("\n[5/5] Creating queries...")
        self.queries = create_queries(self.index, self.applicant, self.spaces)
        logger.info(f"  Created {len(self.queries)} query types")

        # Setup executor
        logger.info("\nSetting up executor...")
        self.source = InMemorySource(self.applicant)
        self.executor = InMemoryExecutor(
            sources=[self.source],
            indices=[self.index]
        )

        # Run and ingest data
        logger.info("Starting executor...")
        self.app = self.executor.run()

        logger.info(f"Ingesting {len(self.data)} records...")
        self.source.put(self.data)

        logger.info("\n" + "=" * 80)
        logger.info("✅ SEARCH SYSTEM READY")
        logger.info("=" * 80)

    def search(
        self,
        query: str,
        query_type: str = "comprehensive",
        min_experience: float = 0.0,
        education: str = None,
        stage: str = "Applied",
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for applicants.

        Args:
            query: Search query text
            query_type: Type of search
                - "comprehensive" (default)
                - "skills_search"
                - "job_search"
                - "recent"
            min_experience: Minimum years of experience
            education: Filter by education level
            stage: Application stage filter
            limit: Number of results

        Returns:
            List of matching applicants
        """
        logger.info(f"\nSearching: '{query}'")
        logger.info(f"  Type: {query_type}")
        logger.info(f"  Min experience: {min_experience}")
        logger.info(f"  Limit: {limit}")

        # Build query params
        params = {
            "query": query,
            "limit": limit,
            "min_exp": min_experience,
            "stage": stage or "Applied"
        }

        if education:
            params["education"] = education

        # Execute query
        query_obj = self.queries.get(query_type, self.queries["comprehensive"])
        result = self.app.query(query_obj, **params)

        logger.info(f"✓ Found {len(result)} results")

        return result

    def format_results(self, results: List[Dict]) -> str:
        """Format search results for display"""
        if not results:
            return "No results found."

        output = []
        output.append(f"\nFound {len(results)} results:\n")
        output.append("=" * 80)

        for i, result in enumerate(results, 1):
            output.append(f"\n[{i}]")
            output.append(f"  Name: {result.get('full_name', 'N/A')}")
            output.append(f"  Job: {result.get('job_title', 'N/A')}")
            output.append(f"  Location: {result.get('location', 'Unknown')}")
            output.append(f"  Experience: {result.get('total_years_experience', 0):.1f} years")
            output.append(f"  Education: {result.get('education_level', 'N/A')}")

            skills = result.get('skills_extracted', '')
            if skills:
                output.append(f"  Skills: {skills[:100]}{'...' if len(skills) > 100 else ''}")

        output.append("\n" + "=" * 80)

        return "\n".join(output)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example usage"""

    # File path
    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/preprocessed_with_gpt_batch.json"

    # Initialize
    logger.info("Initializing Superlinked search system...")
    search_system = SuperlinkedApplicantSearch(DATA_FILE)

    # Example 1: Comprehensive search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 1: Search for Senior Engineers")
    logger.info("=" * 80)

    results = search_system.search(
        query="Senior Civil Engineer with structural design and AutoCAD experience",
        query_type="comprehensive",
        min_experience=5,
        limit=5
    )

    print(search_system.format_results(results))

    # Example 2: Skills search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 2: Search for AutoCAD skills")
    logger.info("=" * 80)

    results = search_system.search(
        query="AutoCAD Revit SketchUp 3D modeling",
        query_type="skills_search",
        min_experience=3,
        limit=5
    )

    print(search_system.format_results(results))

    # Example 3: Job title search
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 3: Search for specific job titles")
    logger.info("=" * 80)

    results = search_system.search(
        query="Project Manager",
        query_type="job_search",
        education="Bachelor's Degree",
        limit=5
    )

    print(search_system.format_results(results))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠ Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
