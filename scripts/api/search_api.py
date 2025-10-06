"""
FastAPI Endpoint for Intelligent Candidate Search
Natural language search for recruiters
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

from core.load_env import load_env
from core.query_parser import GeminiQueryParser
from core.intelligent_search import IntelligentSearchEngine
from core.match_explainer import MatchExplainer

# Load environment
load_env()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
logger.info("Initializing search system...")
parser = GeminiQueryParser()
engine = IntelligentSearchEngine()
explainer = MatchExplainer()
logger.info("✓ Search system ready")

# Create FastAPI app
app = FastAPI(
    title="Intelligent Candidate Search API",
    description="Natural language search for recruiting",
    version="1.0.0"
)


# Request/Response models
class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(
        ...,
        description="Natural language query",
        example="Senior civil engineer in Manila with AutoCAD, 5+ years"
    )
    limit: int = Field(
        20,
        description="Maximum number of results",
        ge=1,
        le=100
    )
    enable_reranking: bool = Field(
        True,
        description="Enable skills-based re-ranking"
    )


class CandidateInfo(BaseModel):
    """Candidate information"""
    id: str
    name: str
    email: str
    job_title: str
    experience_years: float
    tenure_years: float
    location: str
    education: str
    current_company: Optional[str]
    current_stage: Optional[str]
    resume_url: Optional[str]
    date_applied: Optional[int]  # Unix timestamp


class Scores(BaseModel):
    """Match scores"""
    final_score: float
    semantic_score: float
    skills_match_score: float
    vector_breakdown: Dict[str, float]


class SearchResult(BaseModel):
    """Single search result with explanation"""
    candidate: CandidateInfo
    scores: Scores
    match_reasons: List[str]
    resume_snippet: str


class SearchResponse(BaseModel):
    """Complete search response"""
    query: str
    parsed_filters: Dict[str, Any]
    total_results: int
    results: List[SearchResult]


# Endpoints
@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Intelligent Candidate Search API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    try:
        return {
            "status": "healthy",
            "components": {
                "query_parser": "ready",
                "search_engine": "ready",
                "match_explainer": "ready",
                "qdrant_connection": "connected",
                "gemini_api": "connected"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System unhealthy: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_candidates(request: SearchRequest):
    """
    Search for candidates using natural language

    This endpoint:
    1. Parses the natural language query to extract filters
    2. Searches across resume, skills, and tasks vectors
    3. Re-ranks by skills match
    4. Returns candidates with match explanations

    Example query: "Senior Python developer with Django, 3+ years in Manila"
    """
    try:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"API Search Request: '{request.query}'")
        logger.info(f"{'=' * 80}")

        # Step 1: Parse query
        logger.info("[1/3] Parsing natural language query...")
        parsed_query = parser.parse(request.query)

        # Step 2: Search
        logger.info("[2/3] Searching candidates...")
        search_results = engine.search(
            parsed_query,
            limit=request.limit,
            enable_reranking=request.enable_reranking
        )

        # Step 3: Generate explanations
        logger.info("[3/3] Generating match explanations...")
        explained_results = []

        for result in search_results:
            explained = explainer.explain(result, parsed_query)
            explained_results.append(explained)

        # Build response
        response = {
            "query": request.query,
            "parsed_filters": parsed_query['filters'],
            "total_results": len(explained_results),
            "results": explained_results
        }

        logger.info(f"✓ Returning {len(explained_results)} results")
        logger.info(f"{'=' * 80}\n")

        return response

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get search system statistics"""
    try:
        # Get collection info
        collection_info = engine.client.get_collection(engine.COLLECTION_NAME)

        return {
            "total_candidates": collection_info.points_count,
            "collection_name": engine.COLLECTION_NAME,
            "collection_status": collection_info.status,
            "vectors_per_candidate": 3,
            "vector_names": ["resume", "skills", "tasks"],
            "vector_dimension": 3072,
            "embedding_model": "gemini-embedding-001",
            "query_parser_model": "gemini-2.0-flash-001"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Run with: uvicorn search_api:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn

    logger.info("\n" + "=" * 80)
    logger.info("STARTING INTELLIGENT CANDIDATE SEARCH API")
    logger.info("=" * 80)
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("Health Check: http://localhost:8000/health")
    logger.info("=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
