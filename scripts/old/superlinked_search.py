"""
Superlinked Search System with Pre-Generated Gemini Embeddings
Uses embeddings from applicants_with_embeddings.json
No real-time Gemini API calls needed during search!
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Note: Superlinked will be installed separately
# Uncomment when ready:
# from superlinked import framework as sl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

class ApplicantSchema:
    """
    Applicant schema for Superlinked.
    Maps to our preprocessed data structure.
    """

    def __init__(self):
        """Define schema fields matching our data"""
        # When Superlinked is installed, use:
        # self.id = sl.String("id")
        # self.full_name = sl.String("full_name")
        # ... etc

        # For now, just document the schema
        self.fields = {
            # Core fields
            "id": "String",
            "full_name": "String",
            "email": "String",
            "job_title": "String",
            "current_stage": "String",

            # Education
            "education_level": "String",
            "education_raw": "String",

            # Experience
            "total_years_experience": "Float",
            "longest_tenure_years": "Float",
            "current_company": "String",
            "work_history_text": "String",
            "company_names": "String",

            # Skills & Content
            "skills_extracted": "String",
            "resume_full_text": "String",
            "tasks_summary": "String",

            # Location & Time
            "location": "String",
            "date_applied": "Integer (timestamp)",
            "resume_url": "String",

            # PRE-GENERATED EMBEDDINGS (3072-dim each)
            "embedding_resume": "List[float] (3072-dim)",
            "embedding_skills": "List[float] (3072-dim)",
            "embedding_tasks": "List[float] (3072-dim)"
        }


# ============================================================================
# LOAD DATA WITH EMBEDDINGS
# ============================================================================

def load_applicants_with_embeddings(json_file: str) -> List[Dict[str, Any]]:
    """
    Load applicants with pre-generated Gemini embeddings.

    Args:
        json_file: Path to applicants_with_embeddings.json

    Returns:
        List of applicant dictionaries with embeddings
    """
    logger.info(f"Loading applicants with embeddings from {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Verify embeddings exist
        with_embeddings = sum(1 for d in data if d.get("embedding_resume"))

        logger.info(f"✓ Loaded {len(data)} applicants")
        logger.info(f"  {with_embeddings} have embeddings ({with_embeddings/len(data)*100:.1f}%)")

        return data

    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise


# ============================================================================
# VECTOR SEARCH (Without Superlinked)
# ============================================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    import numpy as np

    v1 = np.array(vec1)
    v2 = np.array(vec2)

    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def search_applicants(
    applicants: List[Dict[str, Any]],
    query_embedding: List[float],
    embedding_field: str = "embedding_resume",
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 20
) -> List[Dict[str, Any]]:
    """
    Search applicants using pre-generated embeddings.

    Args:
        applicants: List of applicant data with embeddings
        query_embedding: Query vector (from Gemini)
        embedding_field: Which embedding to search
            - "embedding_resume" (full resume)
            - "embedding_skills" (skills only)
            - "embedding_tasks" (job tasks)
        filters: Optional filters
            - min_experience: Minimum years
            - max_experience: Maximum years
            - location: City name
            - education: Education level
            - stage: Application stage
        top_k: Number of results to return

    Returns:
        List of top matching applicants with similarity scores
    """
    logger.info(f"Searching {len(applicants)} applicants...")
    logger.info(f"  Using field: {embedding_field}")
    logger.info(f"  Filters: {filters}")

    # Calculate similarities
    scored_applicants = []

    for applicant in applicants:
        # Apply filters first
        if filters:
            if "min_experience" in filters:
                if applicant.get("total_years_experience", 0) < filters["min_experience"]:
                    continue

            if "max_experience" in filters:
                if applicant.get("total_years_experience", 999) > filters["max_experience"]:
                    continue

            if "location" in filters:
                if filters["location"].lower() not in applicant.get("location", "").lower():
                    continue

            if "education" in filters:
                if filters["education"] != applicant.get("education_level"):
                    continue

            if "stage" in filters:
                if filters["stage"] != applicant.get("current_stage"):
                    continue

        # Get embedding
        embedding = applicant.get(embedding_field)
        if not embedding or len(embedding) == 0:
            continue

        # Calculate similarity
        similarity = cosine_similarity(query_embedding, embedding)

        # Add to results
        scored_applicants.append({
            **applicant,
            "similarity_score": similarity
        })

    # Sort by similarity
    scored_applicants.sort(key=lambda x: x["similarity_score"], reverse=True)

    # Return top K
    results = scored_applicants[:top_k]

    logger.info(f"✓ Found {len(results)} results")
    if results:
        logger.info(f"  Top score: {results[0]['similarity_score']:.4f}")
        logger.info(f"  Lowest score: {results[-1]['similarity_score']:.4f}")

    return results


# ============================================================================
# SEARCH INTERFACE
# ============================================================================

class ApplicantSearchEngine:
    """
    Simple search engine using pre-generated Gemini embeddings.
    """

    def __init__(self, applicants_file: str):
        """
        Initialize search engine.

        Args:
            applicants_file: Path to applicants_with_embeddings.json
        """
        self.applicants = load_applicants_with_embeddings(applicants_file)

        # Import embedder for queries
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from gemini_embedder_prod import GeminiEmbedder

        self.embedder = GeminiEmbedder()
        logger.info("✓ Search engine initialized")

    def search(
        self,
        query: str,
        search_field: str = "resume",
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        location: Optional[str] = None,
        education: Optional[str] = None,
        stage: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search applicants by natural language query.

        Args:
            query: Natural language search query
                   e.g., "Senior Civil Engineer with AutoCAD experience"
            search_field: Which field to search
                - "resume" (default, full resume text)
                - "skills" (skills only)
                - "tasks" (job responsibilities)
            min_experience: Minimum years of experience
            max_experience: Maximum years of experience
            location: Filter by location (partial match)
            education: Filter by education level (exact match)
            stage: Filter by application stage
            top_k: Number of results to return

        Returns:
            List of matching applicants with scores
        """
        # Generate query embedding
        logger.info(f"Generating embedding for query: '{query}'")
        query_embedding = self.embedder.embed_single(query)

        if not query_embedding or len(query_embedding) == 0:
            logger.error("Failed to generate query embedding")
            return []

        # Map search field to embedding field
        embedding_field_map = {
            "resume": "embedding_resume",
            "skills": "embedding_skills",
            "tasks": "embedding_tasks"
        }

        embedding_field = embedding_field_map.get(search_field, "embedding_resume")

        # Build filters
        filters = {}
        if min_experience is not None:
            filters["min_experience"] = min_experience
        if max_experience is not None:
            filters["max_experience"] = max_experience
        if location:
            filters["location"] = location
        if education:
            filters["education"] = education
        if stage:
            filters["stage"] = stage

        # Search
        results = search_applicants(
            self.applicants,
            query_embedding,
            embedding_field=embedding_field,
            filters=filters,
            top_k=top_k
        )

        return results

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for display"""
        if not results:
            return "No results found."

        output = []
        output.append(f"\nFound {len(results)} results:\n")
        output.append("=" * 80)

        for i, result in enumerate(results, 1):
            output.append(f"\n[{i}] Score: {result['similarity_score']:.4f}")
            output.append(f"    Name: {result.get('full_name', 'N/A')}")
            output.append(f"    Job: {result.get('job_title', 'N/A')}")
            output.append(f"    Location: {result.get('location', 'Unknown')}")
            output.append(f"    Experience: {result.get('total_years_experience', 0):.1f} years")
            output.append(f"    Education: {result.get('education_level', 'N/A')}")

            skills = result.get('skills_extracted', '')
            if skills:
                output.append(f"    Skills: {skills[:100]}{'...' if len(skills) > 100 else ''}")

        output.append("\n" + "=" * 80)

        return "\n".join(output)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Example usage of the search engine"""

    # File paths
    EMBEDDINGS_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json"

    # Initialize search engine
    logger.info("Initializing search engine...")
    search_engine = ApplicantSearchEngine(EMBEDDINGS_FILE)

    # Example 1: Search by job description
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 1: Search for Senior Civil Engineers")
    logger.info("=" * 80)

    results = search_engine.search(
        query="Senior Civil Engineer with structural design experience",
        search_field="resume",
        min_experience=5,
        top_k=5
    )

    print(search_engine.format_results(results))

    # Example 2: Search by skills
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 2: Search for AutoCAD experts")
    logger.info("=" * 80)

    results = search_engine.search(
        query="AutoCAD Revit SketchUp 3D modeling",
        search_field="skills",
        location="Manila",
        top_k=5
    )

    print(search_engine.format_results(results))

    # Example 3: Search by responsibilities
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 3: Search by job responsibilities")
    logger.info("=" * 80)

    results = search_engine.search(
        query="project management construction supervision team leadership",
        search_field="tasks",
        education="Bachelor's Degree",
        top_k=5
    )

    print(search_engine.format_results(results))


if __name__ == "__main__":
    main()
