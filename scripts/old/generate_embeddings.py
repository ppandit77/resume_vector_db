"""
Generate Gemini Embeddings for Applicant Data
Creates embeddings for resume text, skills, and tasks
"""

import json
import logging
import time
from typing import List, Dict, Any
import numpy as np

# Import production embedder
from gemini_embedder_prod import GeminiEmbedder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('generate_embeddings.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_applicant_data(json_file: str) -> List[Dict[str, Any]]:
    """Load preprocessed applicant data"""
    logger.info(f"Loading applicant data from {json_file}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"✓ Loaded {len(data)} applicant records")
        return data

    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise


def generate_embeddings_for_applicants(
    applicants: List[Dict[str, Any]],
    embedder: GeminiEmbedder,
    batch_size: int = 50
) -> List[Dict[str, Any]]:
    """
    Generate embeddings for all applicants.

    Creates embeddings for:
    - resume_full_text (primary semantic search)
    - skills_extracted (skill matching)
    - tasks_summary (job responsibilities)
    """
    logger.info("=" * 80)
    logger.info("GENERATING EMBEDDINGS")
    logger.info("=" * 80)

    total = len(applicants)
    enriched_applicants = []

    # Process in batches to show progress
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = applicants[batch_start:batch_end]

        logger.info(f"\nProcessing batch {batch_start}-{batch_end} of {total}")

        # Extract texts for this batch
        resume_texts = []
        skills_texts = []
        tasks_texts = []

        for applicant in batch:
            # Resume text (main content)
            resume = applicant.get("resume_full_text", "")
            resume_texts.append(resume if resume else "No resume available")

            # Skills
            skills = applicant.get("skills_extracted", "")
            skills_texts.append(skills if skills else "No skills listed")

            # Tasks
            tasks = applicant.get("tasks_summary", "")
            tasks_texts.append(tasks if tasks else "No tasks listed")

        # Generate embeddings for each field type
        logger.info("  Generating resume embeddings...")
        resume_embeddings = embedder.embed_batch(resume_texts, show_progress=False)

        logger.info("  Generating skills embeddings...")
        skills_embeddings = embedder.embed_batch(skills_texts, show_progress=False)

        logger.info("  Generating tasks embeddings...")
        tasks_embeddings = embedder.embed_batch(tasks_texts, show_progress=False)

        # Combine with original data
        for i, applicant in enumerate(batch):
            enriched = applicant.copy()
            enriched["embedding_resume"] = resume_embeddings[i]
            enriched["embedding_skills"] = skills_embeddings[i]
            enriched["embedding_tasks"] = tasks_embeddings[i]
            enriched_applicants.append(enriched)

        logger.info(f"✓ Completed batch {batch_start}-{batch_end}")

        # Brief pause to avoid rate limits
        if batch_end < total:
            time.sleep(1)

    logger.info("\n" + "=" * 80)
    logger.info(f"✓ Generated embeddings for {len(enriched_applicants)} applicants")
    logger.info("=" * 80)

    return enriched_applicants


def save_embeddings(data: List[Dict[str, Any]], output_file: str):
    """Save enriched data with embeddings"""
    logger.info(f"\nSaving embeddings to {output_file}...")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Calculate file size
        import os
        size_mb = os.path.getsize(output_file) / (1024 * 1024)

        logger.info(f"✓ Saved {len(data)} records with embeddings")
        logger.info(f"  File size: {size_mb:.2f} MB")

    except Exception as e:
        logger.error(f"Error saving embeddings: {e}")
        raise


def verify_embeddings(data: List[Dict[str, Any]]):
    """Verify embedding quality"""
    logger.info("\n" + "=" * 80)
    logger.info("VERIFYING EMBEDDINGS")
    logger.info("=" * 80)

    total = len(data)

    # Check completeness
    resume_count = sum(1 for d in data if d.get("embedding_resume") and len(d["embedding_resume"]) > 0)
    skills_count = sum(1 for d in data if d.get("embedding_skills") and len(d["embedding_skills"]) > 0)
    tasks_count = sum(1 for d in data if d.get("embedding_tasks") and len(d["embedding_tasks"]) > 0)

    logger.info(f"\nCompleteness:")
    logger.info(f"  Resume embeddings: {resume_count}/{total} ({resume_count/total*100:.1f}%)")
    logger.info(f"  Skills embeddings:  {skills_count}/{total} ({skills_count/total*100:.1f}%)")
    logger.info(f"  Tasks embeddings:   {tasks_count}/{total} ({tasks_count/total*100:.1f}%)")

    # Check dimensions
    if resume_count > 0:
        sample = next(d for d in data if d.get("embedding_resume") and len(d["embedding_resume"]) > 0)
        resume_dim = len(sample["embedding_resume"])
        skills_dim = len(sample["embedding_skills"]) if sample.get("embedding_skills") else 0
        tasks_dim = len(sample["embedding_tasks"]) if sample.get("embedding_tasks") else 0

        logger.info(f"\nDimensions:")
        logger.info(f"  Resume: {resume_dim}")
        logger.info(f"  Skills: {skills_dim}")
        logger.info(f"  Tasks:  {tasks_dim}")

    # Sample embedding values
    if data:
        sample = data[0]
        logger.info(f"\nSample applicant:")
        logger.info(f"  Name: {sample.get('full_name', 'N/A')}")
        logger.info(f"  Job: {sample.get('job_title', 'N/A')}")
        if sample.get("embedding_resume"):
            logger.info(f"  Resume embedding (first 5): {sample['embedding_resume'][:5]}")

    logger.info("\n" + "=" * 80)
    logger.info("✓ VERIFICATION COMPLETE")
    logger.info("=" * 80)


def main():
    """Main execution"""
    # Paths
    INPUT_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/preprocessed_with_gpt_batch.json"
    OUTPUT_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/applicants_with_embeddings.json"

    try:
        # Load data
        logger.info("STEP 1: Load preprocessed data")
        applicants = load_applicant_data(INPUT_FILE)

        # Initialize embedder
        logger.info("\nSTEP 2: Initialize Gemini embedder")
        embedder = GeminiEmbedder()

        # Generate embeddings
        logger.info("\nSTEP 3: Generate embeddings")
        enriched_data = generate_embeddings_for_applicants(
            applicants,
            embedder,
            batch_size=50  # Process 50 at a time
        )

        # Save
        logger.info("\nSTEP 4: Save embeddings")
        save_embeddings(enriched_data, OUTPUT_FILE)

        # Verify
        logger.info("\nSTEP 5: Verify embeddings")
        verify_embeddings(enriched_data)

        logger.info("\n" + "=" * 80)
        logger.info("✅ EMBEDDING GENERATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Output: {OUTPUT_FILE}")

    except KeyboardInterrupt:
        logger.info("\n⚠ Process interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
