"""
Intelligent Multi-Vector Search Engine
Pre-filtering + Weighted Multi-Vector Fusion + Skills Re-ranking
"""
import os
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range, MatchValue, MatchText, MatchAny
from google import genai

logger = logging.getLogger(__name__)


class IntelligentSearchEngine:
    """
    Multi-vector search engine with:
    - Pre-filtering by metadata
    - Weighted fusion across resume/skills/tasks vectors
    - Skills-based re-ranking
    """

    COLLECTION_NAME = "applicants_unified"

    # Vector weights for fusion
    WEIGHTS = {
        "resume": 0.5,   # 50% - most important
        "skills": 0.3,   # 30% - skill matching
        "tasks": 0.2     # 20% - task experience
    }

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize search engine

        Args:
            qdrant_url: Qdrant Cloud URL (defaults to env var)
            qdrant_api_key: Qdrant API key (defaults to env var)
            gemini_api_key: Gemini API key for embeddings (defaults to env var)
        """
        # Connect to Qdrant
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL')
        self.qdrant_api_key = qdrant_api_key or os.getenv('QDRANT_API_KEY')

        if not self.qdrant_url or not self.qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY required")

        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            timeout=120
        )

        logger.info(f"✓ Connected to Qdrant: {self.qdrant_url}")

        # Initialize Gemini for query embeddings
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY required")

        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        logger.info("✓ Gemini embedder initialized")

        # Verify collection exists
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            logger.info(f"✓ Collection '{self.COLLECTION_NAME}' found with {info.points_count} applicants")
        except Exception as e:
            raise ValueError(f"Collection '{self.COLLECTION_NAME}' not found: {e}")

    def _embed_query(self, text: str) -> List[float]:
        """Generate Gemini embedding for search query (3072-dim)"""
        response = self.gemini_client.models.embed_content(
            model='models/gemini-embedding-001',
            contents=text
        )
        return response.embeddings[0].values

    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Filter]:
        """
        Build Qdrant filter from parsed query filters

        Args:
            filters: Dict with min_experience, max_experience, location, education_level, etc.

        Returns:
            Qdrant Filter object or None
        """
        conditions = []

        # Experience range filter
        if filters.get('min_experience') is not None:
            conditions.append(
                FieldCondition(
                    key="total_years_experience",
                    range=Range(gte=float(filters['min_experience']))
                )
            )

        if filters.get('max_experience') is not None:
            conditions.append(
                FieldCondition(
                    key="total_years_experience",
                    range=Range(lte=float(filters['max_experience']))
                )
            )

        # Location filter (exact match)
        if filters.get('location'):
            conditions.append(
                FieldCondition(
                    key="location",
                    match=MatchValue(value=filters['location'])
                )
            )

        # Education level filter (exact match)
        if filters.get('education_level'):
            conditions.append(
                FieldCondition(
                    key="education_level",
                    match=MatchValue(value=filters['education_level'])
                )
            )

        # Date applied filter (range)
        if filters.get('min_date_applied') is not None:
            conditions.append(
                FieldCondition(
                    key="date_applied",
                    range=Range(gte=int(filters['min_date_applied']))
                )
            )

        if filters.get('max_date_applied') is not None:
            conditions.append(
                FieldCondition(
                    key="date_applied",
                    range=Range(lte=int(filters['max_date_applied']))
                )
            )

        # Job title filter (full-text match)
        if filters.get('desired_job_titles'):
            # Match any of the desired job titles using full-text search
            job_title_conditions = []
            for title in filters['desired_job_titles']:
                job_title_conditions.append(
                    FieldCondition(
                        key="job_title",
                        match=MatchText(text=title)
                    )
                )
            # Use should (OR logic) for multiple job titles
            if len(job_title_conditions) == 1:
                conditions.append(job_title_conditions[0])
            elif len(job_title_conditions) > 1:
                conditions.append(
                    Filter(should=job_title_conditions)
                )

        # Company filter (full-text match on company_names or current_company)
        if filters.get('target_companies'):
            # Match any of the target companies in either company_names or current_company
            company_conditions = []
            for company in filters['target_companies']:
                # Check in company_names (all past companies)
                company_conditions.append(
                    FieldCondition(
                        key="company_names",
                        match=MatchText(text=company)
                    )
                )
                # Also check current_company
                company_conditions.append(
                    FieldCondition(
                        key="current_company",
                        match=MatchText(text=company)
                    )
                )
            # Use should (OR logic) for multiple companies
            if len(company_conditions) > 0:
                conditions.append(
                    Filter(should=company_conditions)
                )

        if not conditions:
            return None

        return Filter(must=conditions)

    def _calculate_skills_match(
        self,
        candidate_skills: str,
        required_skills: List[str]
    ) -> float:
        """
        Calculate skill match score

        Args:
            candidate_skills: Skills text from candidate
            required_skills: List of required skills

        Returns:
            Score 0.0 to 1.0
        """
        if not required_skills or not candidate_skills:
            return 0.0

        candidate_skills_lower = candidate_skills.lower()
        matched = sum(
            1 for skill in required_skills
            if skill.lower() in candidate_skills_lower
        )

        return matched / len(required_skills)

    def search(
        self,
        parsed_query: Dict[str, Any],
        limit: int = 20,
        enable_reranking: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute intelligent search with multi-vector fusion

        Args:
            parsed_query: Output from GeminiQueryParser.parse()
            limit: Number of results to return
            enable_reranking: Whether to re-rank by skills match

        Returns:
            List of candidate dictionaries with scores and metadata
        """
        search_intent = parsed_query['search_intent']
        filters = parsed_query['filters']

        logger.info(f"\n🔍 Searching: '{search_intent}'")

        # Step 1: Generate query embedding
        logger.info("  [1/4] Generating query embedding...")
        query_vector = self._embed_query(search_intent)
        logger.info(f"        ✓ Embedding: {len(query_vector)} dimensions")

        # Step 2: Build metadata filter
        logger.info("  [2/4] Building pre-filters...")
        query_filter = self._build_filter(filters)

        if query_filter:
            logger.info(f"        ✓ Filters applied:")
            if filters.get('min_experience'):
                logger.info(f"          - Experience >= {filters['min_experience']} years")
            if filters.get('max_experience'):
                logger.info(f"          - Experience <= {filters['max_experience']} years")
            if filters.get('location'):
                logger.info(f"          - Location = {filters['location']}")
            if filters.get('education_level'):
                logger.info(f"          - Education = {filters['education_level']}")
            if filters.get('desired_job_titles'):
                logger.info(f"          - Job titles: {', '.join(filters['desired_job_titles'])}")
            if filters.get('target_companies'):
                logger.info(f"          - Companies: {', '.join(filters['target_companies'])}")
            if filters.get('min_date_applied'):
                from datetime import datetime
                date_str = datetime.fromtimestamp(filters['min_date_applied']).strftime('%Y-%m-%d')
                logger.info(f"          - Applied after: {date_str}")
        else:
            logger.info(f"        ✓ No pre-filters (searching all candidates)")

        # Step 3: Multi-vector search with weighted fusion
        logger.info("  [3/4] Searching 3 vectors (resume, skills, tasks)...")

        # Search each vector
        all_results = {}

        for vector_name, weight in self.WEIGHTS.items():
            logger.info(f"        - Searching '{vector_name}' vector (weight: {weight})...")

            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=(vector_name, query_vector),
                query_filter=query_filter,
                limit=limit * 2,  # Get more for re-ranking
                with_payload=True,
                score_threshold=0.3  # Minimum similarity
            )

            logger.info(f"          ✓ Found {len(results)} matches")

            # Merge by point ID with weighted scores
            for result in results:
                point_id = result.id
                weighted_score = result.score * weight

                if point_id not in all_results:
                    all_results[point_id] = {
                        "id": point_id,
                        "semantic_score": weighted_score,
                        "vector_scores": {vector_name: result.score},
                        "payload": result.payload
                    }
                else:
                    # Add weighted score
                    all_results[point_id]["semantic_score"] += weighted_score
                    all_results[point_id]["vector_scores"][vector_name] = result.score

        logger.info(f"        ✓ Merged: {len(all_results)} unique candidates")

        # Convert to list
        candidates = list(all_results.values())

        # Step 4: Re-rank with skills matching
        if enable_reranking and filters.get('required_skills'):
            logger.info(f"  [4/4] Re-ranking by skills match...")
            logger.info(f"        Required skills: {', '.join(filters['required_skills'])}")

            for candidate in candidates:
                skills_text = candidate['payload'].get('skills_extracted', '')
                skills_match = self._calculate_skills_match(
                    skills_text,
                    filters['required_skills']
                )

                # Combined score: 70% semantic + 30% skills
                candidate['skills_match_score'] = skills_match
                candidate['final_score'] = (
                    candidate['semantic_score'] * 0.7 +
                    skills_match * 0.3
                )

            # Sort by final score
            candidates.sort(key=lambda x: x['final_score'], reverse=True)
            logger.info(f"        ✓ Re-ranked by combined score (70% semantic + 30% skills)")
        else:
            logger.info(f"  [4/4] Skipping re-ranking (no required skills)")
            # Just use semantic score
            for candidate in candidates:
                candidate['skills_match_score'] = 0.0
                candidate['final_score'] = candidate['semantic_score']

            candidates.sort(key=lambda x: x['final_score'], reverse=True)

        # Return top N
        top_candidates = candidates[:limit]

        logger.info(f"\n✓ Found {len(top_candidates)} candidates")
        if top_candidates:
            logger.info(f"  Top score: {top_candidates[0]['final_score']:.3f}")
            logger.info(f"  Lowest score: {top_candidates[-1]['final_score']:.3f}")

        return top_candidates


# Test the search engine
if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(__file__))
    from load_env import load_env
    from query_parser import GeminiQueryParser

    load_env()

    logging.basicConfig(level=logging.INFO)

    # Initialize
    parser = GeminiQueryParser()
    engine = IntelligentSearchEngine()

    print("\n" + "=" * 80)
    print("TESTING INTELLIGENT SEARCH ENGINE")
    print("=" * 80)

    # Test queries
    test_queries = [
        "Senior civil engineer in Manila with AutoCAD, 5+ years",
        "Python developer with Django",
        "Recent graduate with marketing skills"
    ]

    for query in test_queries:
        print(f"\n{'─' * 80}")
        print(f"Query: {query}")
        print('─' * 80)

        # Parse query
        parsed = parser.parse(query)

        # Search
        results = engine.search(parsed, limit=5)

        # Display results
        print(f"\nTop {len(results)} results:")
        for i, result in enumerate(results, 1):
            payload = result['payload']
            print(f"\n[{i}] {payload.get('full_name', 'N/A')}")
            print(f"    Job: {payload.get('job_title', 'N/A')}")
            print(f"    Experience: {payload.get('total_years_experience', 0):.1f} years")
            print(f"    Location: {payload.get('location', 'N/A')}")
            print(f"    Score: {result['final_score']:.3f} (semantic: {result['semantic_score']:.3f}, skills: {result['skills_match_score']:.2f})")

    print("\n" + "=" * 80)
    print("✓ All tests complete")
    print("=" * 80)
