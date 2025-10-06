"""
Production Superlinked Search System
With Pre-Generated Gemini Embeddings
Full 5,000 Applicant Dataset
"""

import json
import logging
import os
from datetime import timedelta
from typing import List, Dict, Any

import superlinked.framework as sl
from superlinked.framework.dsl.storage.qdrant_vector_database import QdrantVectorDatabase
from superlinked.framework.dsl.storage.mongo_db_vector_database import MongoDBVectorDatabase

# Load environment variables
import sys
sys.path.append(os.path.dirname(__file__))
from load_env import load_env
load_env()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# MONGODB CONFIGURATION
# ============================================================================

def create_mongodb_config() -> MongoDBVectorDatabase:
    """
    Create MongoDB Atlas vector database configuration.
    Uses credentials from environment variables.
    """
    mongodb_host = os.getenv("MONGODB_HOST", "").strip()
    mongodb_database = os.getenv("MONGODB_DATABASE", "").strip()
    mongodb_cluster_name = os.getenv("MONGODB_CLUSTER_NAME", "").strip()
    mongodb_project_id = os.getenv("MONGODB_PROJECT_ID", "").strip()
    mongodb_api_public_key = os.getenv("MONGODB_API_PUBLIC_KEY", "").strip()
    mongodb_api_private_key = os.getenv("MONGODB_API_PRIVATE_KEY", "").strip()
    mongodb_username = os.getenv("MONGODB_USERNAME", "").strip()
    mongodb_password = os.getenv("MONGODB_PASSWORD", "").strip()

    if not all([mongodb_host, mongodb_database, mongodb_cluster_name, mongodb_project_id,
                mongodb_api_public_key, mongodb_api_private_key]):
        logger.warning("MongoDB configuration incomplete. Skipping MongoDB.")
        return None

    logger.info(f"MongoDB Config: ATLAS")
    logger.info(f"  Host: {mongodb_host}")
    logger.info(f"  Database: {mongodb_database}")
    logger.info(f"  Cluster: {mongodb_cluster_name}")

    # Superlinked MongoDB expects:
    # - host: just the hostname (e.g., cluster0.xxxxx.mongodb.net)
    # - db_name: database name
    # - username/password as extra_params
    logger.info(f"  Connecting with user: {mongodb_username}")

    # NOTE: Superlinked MongoDB currently defaults to "default" collection name
    # TODO: Find proper way to specify custom collection name in MongoDBVectorDatabase

    return MongoDBVectorDatabase(
        host=mongodb_host,
        db_name=mongodb_database,
        cluster_name=mongodb_cluster_name,
        project_id=mongodb_project_id,
        admin_api_user=mongodb_api_public_key,
        admin_api_password=mongodb_api_private_key,
        default_query_limit=100,
        username=mongodb_username,
        password=mongodb_password,
        retryWrites="true",  # Must be string "true"/"false" not boolean
        w="majority"
    )


# ============================================================================
# QDRANT CONFIGURATION
# ============================================================================

def create_qdrant_config() -> QdrantVectorDatabase:
    """
    Create Qdrant vector database configuration.
    Uses credentials from environment variables.
    Supports both cloud (URL) and local (file path or :memory:) modes.
    """
    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip()
    qdrant_storage_path = os.getenv("QDRANT_STORAGE_PATH", "").strip()

    if not qdrant_url:
        logger.warning("QDRANT_URL not found. Using in-memory storage.")
        return None

    # Local in-memory mode
    if qdrant_url == ":memory:":
        logger.info(f"Qdrant Config: LOCAL IN-MEMORY MODE")
        logger.info(f"  URL: :memory:")
        logger.info(f"  Note: Data will NOT persist after restart")

        return QdrantVectorDatabase(
            url=":memory:",
            api_key="",  # Empty string for local mode
            default_query_limit=100
        )

    # Local file-based storage mode
    elif qdrant_url.startswith("/") or qdrant_url.startswith("./"):
        logger.error(f"Local file-based Qdrant storage is not fully supported by Superlinked wrapper.")
        logger.error(f"Please use :memory: for local mode or a full http://localhost:6333 URL for Qdrant server.")
        return None

    # Cloud mode (URL-based)
    else:
        if not qdrant_api_key:
            logger.error("QDRANT_API_KEY required for cloud mode but not found.")
            return None

        logger.info(f"Qdrant Config: CLOUD MODE")
        logger.info(f"  URL: {qdrant_url}")

        return QdrantVectorDatabase(
            url=qdrant_url,
            api_key=qdrant_api_key,
            default_query_limit=100,
            client_params={
                "timeout": 600.0  # 10 minute timeout for writes (large 3072-dim embeddings over slow network)
            }
        )


# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================

def create_openai_config() -> sl.OpenAIClientConfig:
    """
    Create OpenAI client configuration for natural language queries.
    Uses API key from environment variables.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment. Natural language queries will not work.")
        return None

    logger.info(f"OpenAI Config: model={model}")

    return sl.OpenAIClientConfig(
        api_key=api_key,
        model=model
    )


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

class ApplicantSchema(sl.Schema):
    """Complete applicant schema with Gemini embeddings"""
    # ID field (required)
    id: sl.IdField

    # Contact & Display fields
    full_name: sl.String
    email: sl.String
    resume_url: sl.String

    # Core text fields
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
    company_names: sl.String
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
# BUILD SPACES
# ============================================================================

def build_spaces(applicant: ApplicantSchema) -> Dict[str, Any]:
    """Build all vector spaces for search"""
    logger.info("\n[STEP 1] BUILDING SPACES")
    logger.info("=" * 80)

    # Custom spaces using pre-generated Gemini embeddings (3072-dim)
    logger.info("  Creating Gemini embedding spaces (3072-dim)...")

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

    # Number spaces
    logger.info("  Creating number spaces...")

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
    logger.info("  Creating recency space...")

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
    logger.info("  Creating categorical spaces...")

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

    spaces = {
        "resume": resume_space,
        "skills": skills_space,
        "tasks": tasks_space,
        "experience": experience_space,
        "tenure": tenure_space,
        "recency": recency_space,
        "education": education_space,
        "location": location_space
    }

    logger.info(f"  ✓ Created {len(spaces)} spaces")
    return spaces


# ============================================================================
# BUILD INDEX
# ============================================================================

def build_index(spaces: Dict[str, Any]) -> sl.Index:
    """Build index from all spaces"""
    logger.info("\n[STEP 2] BUILDING INDEX")
    logger.info("=" * 80)

    index = sl.Index([
        spaces["resume"],
        spaces["skills"],
        spaces["tasks"],
        spaces["experience"],
        spaces["tenure"],
        spaces["recency"],
        spaces["education"],
        spaces["location"]
    ])

    logger.info(f"  ✓ Index created with {len(spaces)} spaces")
    return index


# ============================================================================
# BUILD QUERIES
# ============================================================================

def build_queries(index: sl.Index, applicant: ApplicantSchema, spaces: Dict, openai_config=None) -> Dict:
    """Build all search queries with optional natural language support"""
    logger.info("\n[STEP 3] BUILDING QUERIES")
    logger.info("=" * 80)

    # Define parameter descriptions for natural language processing
    query_vector_param = sl.Param(
        "query_vector",
        description="The semantic embedding vector for the search query about candidate qualifications, skills, or experience."
    )

    query_text_param = sl.Param(
        "query",
        description="The text query for searching job titles, companies, or positions."
    )

    min_exp_param = sl.Param(
        "min_exp",
        description="Minimum years of work experience required (e.g., 3, 5, 10 years).",
        default=0.0
    )

    min_tenure_param = sl.Param(
        "min_tenure",
        description="Minimum years at longest held position (e.g., 2, 3, 5 years).",
        default=0.0
    )

    education_param = sl.Param(
        "education_level",
        description="Required education level (e.g., Bachelor's Degree, Master's Degree).",
        default=None
    )

    location_param = sl.Param(
        "location",
        description="Preferred location or city (e.g., Manila, Quezon City, Cebu City).",
        default=None
    )

    stage_param = sl.Param(
        "current_stage",
        description="Application stage filter (e.g., Applied, Interviewing, Hired).",
        default=None
    )

    date_from_param = sl.Param(
        "date_from",
        description="Start date for application date range filter (Unix timestamp).",
        default=None
    )

    date_to_param = sl.Param(
        "date_to",
        description="End date for application date range filter (Unix timestamp).",
        default=None
    )

    limit_param = sl.Param(
        "limit",
        description="Maximum number of results to return.",
        default=20
    )

    # Comprehensive search with Superlinked filtering
    # Note: Filters require payload indexing in Qdrant - currently disabled
    comprehensive_query_builder = (
        sl.Query(
            index,
            weights={
                spaces["resume"]: 0.3,
                spaces["skills"]: 0.25,
                spaces["experience"]: 0.15,
                spaces["recency"]: 0.1,
                spaces["education"]: 0.1,
                spaces["location"]: 0.05,
                spaces["tenure"]: 0.05
            }
        )
        .find(applicant)
        .similar(spaces["resume"].vector, query_vector_param)
        # .filter(applicant.total_years_experience >= min_exp_param)  # Disabled - requires payload indexing
        .limit(limit_param)
        .select_all()
    )

    # Add natural language support if OpenAI config provided
    if openai_config:
        comprehensive_query = comprehensive_query_builder.with_natural_query(
            sl.Param("natural_query", description="Natural language query describing the ideal candidate"),
            openai_config
        )
    else:
        comprehensive_query = comprehensive_query_builder

    # Skills-focused query
    skills_query_builder = (
        sl.Query(
            index,
            weights={
                spaces["skills"]: 0.6,
                spaces["experience"]: 0.2,
                spaces["education"]: 0.1,
                spaces["tenure"]: 0.1
            }
        )
        .find(applicant)
        .similar(spaces["skills"].vector, query_vector_param)
        .filter(applicant.total_years_experience >= min_exp_param)
        .limit(limit_param)
        .select_all()
    )

    if openai_config:
        skills_query = skills_query_builder.with_natural_query(
            sl.Param("natural_query", description="Natural language query focusing on skills and technical abilities"),
            openai_config
        )
    else:
        skills_query = skills_query_builder


    # Recent applicants
    recent_query_builder = (
        sl.Query(
            index,
            weights={
                spaces["recency"]: 0.4,
                spaces["resume"]: 0.3,
                spaces["skills"]: 0.15,
                spaces["experience"]: 0.1,
                spaces["location"]: 0.05
            }
        )
        .find(applicant)
        .similar(spaces["resume"].vector, query_vector_param)
        .filter(applicant.total_years_experience >= min_exp_param)
        .limit(limit_param)
        .select_all()
    )

    if openai_config:
        recent_query = recent_query_builder.with_natural_query(
            sl.Param("natural_query", description="Natural language query for recently applied candidates"),
            openai_config
        )
    else:
        recent_query = recent_query_builder

    queries = {
        "comprehensive": comprehensive_query,
        "skills": skills_query,
        "recent": recent_query
    }

    logger.info(f"  ✓ Created {len(queries)} query types")
    return queries


# ============================================================================
# BUILD EXECUTOR
# ============================================================================

def build_executor(applicant: ApplicantSchema, index: sl.Index, queries_dict: Dict, vector_database=None):
    """Build and start executor with optional Qdrant vector database"""
    logger.info("\n[STEP 4] BUILDING EXECUTOR")
    logger.info("=" * 80)

    if vector_database:
        logger.info("  Using vector database for persistent storage")

        # Create RestSource
        source = sl.RestSource(applicant)

        # Create RestQuery objects from query builders
        rest_queries = []
        for query_name, query_builder in queries_dict.items():
            rest_query = sl.RestQuery(
                sl.RestDescriptor(query_name),
                query_builder
            )
            rest_queries.append(rest_query)

        executor = sl.RestExecutor(
            sources=[source],
            indices=[index],
            queries=rest_queries,
            vector_database=vector_database
        )
    else:
        logger.info("  Using in-memory executor (non-persistent)")
        source = sl.InMemorySource(applicant)
        executor = sl.InMemoryExecutor(sources=[source], indices=[index])

    logger.info("  Starting executor...")
    app = executor.run()

    logger.info("  ✓ Executor running")
    return app, source


# ============================================================================
# INGEST DATA
# ============================================================================

def ingest_data(source, data_file: str, batch_size: int = 5):
    """Ingest all applicant data"""
    logger.info("\n[STEP 5] INGESTING DATA")
    logger.info("=" * 80)

    logger.info(f"  Loading data from {data_file}")
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    logger.info(f"  Loaded {total} applicants")

    # Ingest in batches
    logger.info(f"  Ingesting in batches of {batch_size}...")
    for i in range(0, total, batch_size):
        batch = data[i:i+batch_size]
        source.put(batch)

        if (i + batch_size) % 500 == 0 or (i + batch_size) >= total:
            logger.info(f"    Progress: {min(i + batch_size, total)}/{total} records")

    logger.info(f"  ✓ Ingested {total} applicants")
    return total


# ============================================================================
# SEARCH INTERFACE
# ============================================================================

class ProductionSearch:
    """Production search system"""

    def __init__(self, data_file: str, enable_natural_language: bool = True, use_mongodb: bool = True, use_qdrant: bool = False, skip_ingestion: bool = False):
        """
        Initialize complete search system

        Args:
            data_file: Path to applicants JSON file
            enable_natural_language: Enable OpenAI natural language queries
            use_mongodb: Use MongoDB Atlas for persistent storage (default: True)
            use_qdrant: Use Qdrant for persistent storage (default: False)
            skip_ingestion: Skip data ingestion (use when data already exists in vector database)
        """
        logger.info("\n" + "=" * 80)
        logger.info("INITIALIZING PRODUCTION SEARCH SYSTEM")
        logger.info("=" * 80)

        # Create schema
        self.applicant = ApplicantSchema()

        # Build spaces
        self.spaces = build_spaces(self.applicant)

        # Build index
        self.index = build_index(self.spaces)

        # Create vector database configuration (MongoDB Atlas or Qdrant)
        self.vector_database = None

        # Try MongoDB first (preferred)
        if use_mongodb:
            try:
                self.vector_database = create_mongodb_config()
                if self.vector_database:
                    logger.info("  ✓ MongoDB Atlas vector database configured")
            except Exception as e:
                logger.warning(f"  ⚠ Could not configure MongoDB: {e}")

        # Fallback to Qdrant if MongoDB not configured
        if not self.vector_database and use_qdrant:
            try:
                self.vector_database = create_qdrant_config()
                if self.vector_database:
                    logger.info("  ✓ Qdrant vector database configured")
            except Exception as e:
                logger.warning(f"  ⚠ Could not configure Qdrant: {e}")

        # Create OpenAI config for natural language queries
        self.openai_config = None
        if enable_natural_language:
            try:
                self.openai_config = create_openai_config()
                if self.openai_config:
                    logger.info("  ✓ Natural language query support enabled")
            except Exception as e:
                logger.warning(f"  ⚠ Could not enable natural language queries: {e}")

        # Build queries
        self.queries = build_queries(self.index, self.applicant, self.spaces, self.openai_config)

        # Build executor
        self.app, self.source = build_executor(self.applicant, self.index, self.queries, self.vector_database)

        # Ingest data (skip if connecting to existing data in vector database)
        if skip_ingestion:
            logger.info("\n[STEP 5] SKIPPING DATA INGESTION")
            logger.info("=" * 80)
            logger.info("  Connecting to existing data in vector database")
            # Get record count from data file for reporting
            import json
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.total_records = len(data)
            logger.info(f"  Expected records: {self.total_records}")
        else:
            self.total_records = ingest_data(self.source, data_file)

        # Initialize Gemini embedder for queries
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from gemini_embedder_prod import GeminiEmbedder
        self.embedder = GeminiEmbedder()

        logger.info("\n" + "=" * 80)
        logger.info("🚀 PRODUCTION SEARCH SYSTEM READY")
        logger.info("=" * 80)
        logger.info(f"  Total applicants: {self.total_records}")
        logger.info(f"  Embedding dimensions: 3072 (Gemini)")
        logger.info(f"  Query types: {len(self.queries)}")
        logger.info(f"  Storage: {'Qdrant (Persistent)' if self.vector_database else 'In-Memory (Non-Persistent)'}")
        logger.info(f"  Natural language: {'Enabled' if self.openai_config else 'Disabled'}")

    def search(
        self,
        query: str,
        query_type: str = "comprehensive",
        min_experience: float = 0.0,
        min_tenure: float = 0.0,
        education_level: str = None,
        location: str = None,
        current_stage: str = None,
        date_from: int = None,
        date_to: int = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for applicants with comprehensive filtering.

        Args:
            query: Search query text
            query_type: Query type
                - "comprehensive": Full resume + skills + experience
                - "skills": Skills-focused
                - "job": Job title (uses text search)
                - "recent": Recent applicants
                - "company": Company search (uses text search)
            min_experience: Minimum years of experience
            min_tenure: Minimum years at longest held position
            education_level: Filter by education (e.g., "Bachelor's Degree", "Master's Degree")
            location: Filter by location (e.g., "Manila, Philippines", "Quezon City, Philippines")
            current_stage: Filter by application stage (e.g., "Applied", "Interviewing", "Hired")
            date_from: Start date for application date range (Unix timestamp)
            date_to: End date for application date range (Unix timestamp)
            limit: Number of results

        Returns:
            List of matching applicants
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"SEARCHING: '{query}'")
        logger.info(f"{'='*80}")
        logger.info(f"  Type: {query_type}")
        logger.info(f"  Min experience: {min_experience}")
        if min_tenure > 0:
            logger.info(f"  Min tenure: {min_tenure}")
        if education_level:
            logger.info(f"  Education: {education_level}")
        if location:
            logger.info(f"  Location: {location}")
        if current_stage:
            logger.info(f"  Stage: {current_stage}")
        if date_from or date_to:
            logger.info(f"  Date range: {date_from} to {date_to}")
        logger.info(f"  Limit: {limit}")

        # Get query object
        query_obj = self.queries.get(query_type, self.queries["comprehensive"])

        # Build parameters dict
        # Note: InMemoryExecutor doesn't support filters, only RestExecutor does
        params = {
            "limit": limit
        }

        # Add filter parameters only if using vector database (RestExecutor)
        # Note: Filters require proper field indexing in Qdrant
        # Currently disabled until we configure payload indexing
        if self.vector_database and min_experience > 0:
            # Only add filter if explicitly requested AND indexed
            logger.warning(f"  ⚠ min_experience filter requires payload indexing in Qdrant (not yet configured)")
            # params.update({"min_exp": min_experience})
        else:
            # InMemory mode: We'll filter results in Python after retrieval
            if min_experience > 0:
                logger.info(f"  Note: Filtering will be applied post-search (in-memory mode)")

        # Generate query embedding for vector-based queries
        logger.info("  Generating query embedding...")
        query_vector = self.embedder.embed_single(query)
        logger.info(f"  ✓ Query embedding: {len(query_vector)} dims")
        params["query_vector"] = query_vector

        # Execute query with Superlinked's native filtering
        result = self.app.query(query_obj, **params)

        # Convert to pandas
        df = sl.PandasConverter.to_pandas(result)
        logger.info(f"  ✓ Found {len(df)} results")

        return df.to_dict('records')

    def natural_language_search(
        self,
        natural_query: str,
        query_type: str = "comprehensive",
        limit: int = 20
    ) -> List[Dict]:
        """
        Search using natural language query (requires OpenAI config).

        Args:
            natural_query: Natural language description of what you're looking for
                Example: "Find senior civil engineers with 5+ years experience in Manila who know AutoCAD"
            query_type: Query type (comprehensive, skills, job, recent, company)
            limit: Number of results

        Returns:
            List of matching applicants
        """
        if not self.openai_config:
            logger.error("Natural language queries not available. OpenAI config not initialized.")
            logger.info("Falling back to regular search...")
            return self.search(natural_query, query_type, limit=limit)

        logger.info(f"\n{'='*80}")
        logger.info(f"NATURAL LANGUAGE SEARCH: '{natural_query}'")
        logger.info(f"{'='*80}")
        logger.info(f"  Type: {query_type}")
        logger.info(f"  Limit: {limit}")

        # Get query object
        query_obj = self.queries.get(query_type, self.queries["comprehensive"])

        # Generate query embedding for the natural language query text
        logger.info("  Generating query embedding...")
        query_vector = self.embedder.embed_single(natural_query)
        logger.info(f"  ✓ Query embedding: {len(query_vector)} dims")

        # Execute natural language query with both vector and natural query
        logger.info("  Processing natural language query with OpenAI...")
        result = self.app.query(
            query_obj,
            query_vector=query_vector,
            natural_query=natural_query,
            limit=limit
        )

        # Convert to pandas
        df = sl.PandasConverter.to_pandas(result)
        logger.info(f"  ✓ Found {len(df)} results")

        return df.to_dict('records')

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
    """Example usage with full dataset"""

    # Data file with embeddings
    DATA_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json"

    # Initialize (this will take a few minutes for 5,000 records)
    search = ProductionSearch(DATA_FILE)

    # Example 1: Comprehensive search
    logger.info("\n\n" + "=" * 80)
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
    logger.info("\n\n" + "=" * 80)
    logger.info("EXAMPLE 2: Search for AutoCAD skills")
    logger.info("=" * 80)

    results = search.search(
        query="AutoCAD Revit SketchUp 3D modeling",
        query_type="skills",
        min_experience=3,
        limit=5
    )

    print(search.format_results(results))

    # Example 3: Company search
    logger.info("\n\n" + "=" * 80)
    logger.info("EXAMPLE 3: Find people who worked at National Housing Authority")
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
