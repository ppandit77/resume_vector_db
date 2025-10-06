"""
Simple Qdrant Search System
Direct semantic search with metadata filtering (no Superlinked)
"""
import os
import json
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, Range
from dotenv import load_dotenv
import logging
from google import genai

logger = logging.getLogger(__name__)

class SimpleQdrantSearch:
    """Simple semantic search using Qdrant + Gemini embeddings"""

    def __init__(self, data_file: str):
        """Initialize search system

        Args:
            data_file: Path to JSON file with embeddings
        """
        load_dotenv()

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=os.getenv('QDRANT_URL'),
            api_key=os.getenv('QDRANT_API_KEY'),
            timeout=120
        )

        # Initialize Gemini for query embeddings
        self.gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

        # Collection names
        self.resume_collection = "applicants_resume"
        self.skills_collection = "applicants_skills"
        self.tasks_collection = "applicants_tasks"

        # Load data
        logger.info(f"Loading data from {data_file}...")
        with open(data_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        logger.info(f"✓ Loaded {len(self.data)} applicants")

    def create_collections(self):
        """Create 3 Qdrant collections for resume, skills, and tasks embeddings"""
        logger.info("\nCreating Qdrant collections...")

        collections_config = [
            (self.resume_collection, "Resume embeddings"),
            (self.skills_collection, "Skills embeddings"),
            (self.tasks_collection, "Tasks embeddings")
        ]

        for collection_name, description in collections_config:
            try:
                # Delete if exists
                try:
                    self.client.delete_collection(collection_name)
                    logger.info(f"  Deleted existing collection: {collection_name}")
                except:
                    pass

                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=3072,  # Gemini embedding dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"  ✓ Created collection: {collection_name} ({description})")
            except Exception as e:
                logger.error(f"  ✗ Failed to create {collection_name}: {e}")
                raise

    def upload_data(self, batch_size: int = 50):
        """Upload data to all 3 collections"""
        logger.info(f"\nUploading {len(self.data)} applicants to Qdrant...")

        collections = [
            (self.resume_collection, "embedding_resume"),
            (self.skills_collection, "embedding_skills"),
            (self.tasks_collection, "embedding_tasks")
        ]

        for collection_name, embedding_field in collections:
            logger.info(f"\n  Uploading to {collection_name}...")
            points = []

            for i, applicant in enumerate(self.data):
                # Prepare metadata payload
                payload = {
                    "applicant_id": applicant.get("id"),
                    "full_name": applicant.get("full_name"),
                    "email": applicant.get("email"),
                    "job_title": applicant.get("job_title"),
                    "current_stage": applicant.get("current_stage"),
                    "education_level": applicant.get("education_level"),
                    "total_years_experience": float(applicant.get("total_years_experience", 0)),
                    "longest_tenure_years": float(applicant.get("longest_tenure_years", 0)),
                    "current_company": applicant.get("current_company"),
                    "location": applicant.get("location"),
                    "skills_extracted": applicant.get("skills_extracted"),
                    "resume_full_text": applicant.get("resume_full_text"),
                    "resume_url": applicant.get("resume_url"),
                    "date_applied": applicant.get("date_applied")
                }

                # Get embedding vector
                vector = applicant.get(embedding_field, [])

                if len(vector) != 3072:
                    logger.warning(f"    Skipping applicant {i}: invalid embedding dimension {len(vector)}")
                    continue

                # Create point
                point = PointStruct(
                    id=i,
                    vector=vector,
                    payload=payload
                )
                points.append(point)

                # Upload in batches
                if len(points) >= batch_size:
                    self.client.upsert(collection_name=collection_name, points=points)
                    logger.info(f"    ✓ Uploaded {len(points)} points (total: {i+1})")
                    points = []

            # Upload remaining points
            if points:
                self.client.upsert(collection_name=collection_name, points=points)
                logger.info(f"    ✓ Uploaded final {len(points)} points")

            # Verify count
            count = self.client.count(collection_name).count
            logger.info(f"  ✓ {collection_name}: {count} points stored")

    def embed_query(self, query: str) -> List[float]:
        """Generate Gemini embedding for search query"""
        result = self.gemini_client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=query,
            config={
                'response_modalities': ['TEXT'],
                'temperature': 0.0
            }
        )

        # Extract embedding
        embedding = result.candidates[0].content.parts[0].embedding
        return embedding

    def search(
        self,
        query: str,
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        location: Optional[str] = None,
        education_level: Optional[str] = None,
        skills_keywords: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search across all 3 embeddings and merge results

        Args:
            query: Natural language search query
            min_experience: Minimum years of experience
            max_experience: Maximum years of experience
            location: Location filter
            education_level: Education level filter
            skills_keywords: List of required skills
            limit: Max results per collection (final will be deduplicated)

        Returns:
            List of matching applicants sorted by relevance
        """
        logger.info(f"\nSearching for: '{query}'")

        # Generate query embedding
        logger.info("  Generating query embedding...")
        query_vector = self.embed_query(query)
        logger.info(f"  ✓ Query embedding: {len(query_vector)} dims")

        # Build filter
        filter_conditions = []

        if min_experience is not None:
            filter_conditions.append(
                FieldCondition(
                    key="total_years_experience",
                    range=Range(gte=min_experience)
                )
            )
            logger.info(f"  Filter: experience >= {min_experience}")

        if max_experience is not None:
            filter_conditions.append(
                FieldCondition(
                    key="total_years_experience",
                    range=Range(lte=max_experience)
                )
            )
            logger.info(f"  Filter: experience <= {max_experience}")

        if location:
            filter_conditions.append(
                FieldCondition(
                    key="location",
                    match={"value": location}
                )
            )
            logger.info(f"  Filter: location = {location}")

        if education_level:
            filter_conditions.append(
                FieldCondition(
                    key="education_level",
                    match={"value": education_level}
                )
            )
            logger.info(f"  Filter: education = {education_level}")

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Search all 3 collections
        all_results = []

        collections = [
            (self.resume_collection, "resume", 0.5),  # weight
            (self.skills_collection, "skills", 0.3),
            (self.tasks_collection, "tasks", 0.2)
        ]

        for collection_name, source, weight in collections:
            logger.info(f"\n  Searching {collection_name}...")

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )

            logger.info(f"    ✓ Found {len(results)} results")

            for result in results:
                # Apply weight to score
                weighted_score = result.score * weight

                all_results.append({
                    "source": source,
                    "score": weighted_score,
                    "original_score": result.score,
                    **result.payload
                })

        # Deduplicate by applicant_id and sum scores
        merged_results = {}

        for result in all_results:
            applicant_id = result["applicant_id"]

            if applicant_id not in merged_results:
                merged_results[applicant_id] = result.copy()
                merged_results[applicant_id]["sources"] = [result["source"]]
            else:
                # Add weighted score
                merged_results[applicant_id]["score"] += result["score"]
                merged_results[applicant_id]["sources"].append(result["source"])

        # Sort by combined score
        final_results = sorted(
            merged_results.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:limit]

        logger.info(f"\n✓ Merged results: {len(final_results)} unique applicants")

        return final_results
