"""
Production-Ready Batch Processing for Applicant Data Extraction
✅ Logging with multiple levels
✅ API keys from .env (never hardcoded)
✅ Timeout + comprehensive error handling
✅ Output validated with Pydantic
✅ Fallback to rule-based extraction if API fails
✅ Edge case handling
"""

import os
import json
import csv
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field, ValidationError

# Load environment
import sys
sys.path.append(os.path.dirname(__file__))
from load_env import load_env
load_env()

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR VALIDATION
# ============================================================================

class WorkExperienceEntry(BaseModel):
    """Single work experience entry"""
    company: str = Field(default="")
    start_date: str = Field(default="")
    end_date: str = Field(default="")
    years: float = Field(default=0.0, ge=0.0, le=60.0)


class WorkExperience(BaseModel):
    """Complete work experience data"""
    entries: List[WorkExperienceEntry] = Field(default_factory=list)


class ExtractedData(BaseModel):
    """Validated structure for GPT extraction"""
    location: str = Field(default="Unknown")
    skills: List[str] = Field(default_factory=list)
    work_experience: WorkExperience = Field(default_factory=WorkExperience)


class ApplicantRecord(BaseModel):
    """Complete applicant record with validation"""
    id: str
    full_name: str
    email: str
    job_title: str
    current_stage: str = "Applied"
    education_level: str
    education_raw: str = ""
    total_years_experience: float = Field(ge=0.0, le=60.0)
    longest_tenure_years: float = Field(ge=0.0, le=60.0)
    current_company: str = ""
    work_history_text: str = ""
    company_names: str = ""
    skills_extracted: str = ""
    skills_raw_text: str = ""
    resume_full_text: str = ""
    tasks_summary: str = ""
    location: str = "Unknown"
    date_applied: int
    resume_url: str = ""


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration with validation"""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.batch_timeout = int(os.getenv("BATCH_TIMEOUT", "86400"))  # 24 hours
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))

        # Validate required keys
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        logger.info(f"Configuration loaded: model={self.openai_model}")


config = Config()


# ============================================================================
# FALLBACK EXTRACTION (Rule-Based)
# ============================================================================

class FallbackExtractor:
    """Rule-based extraction when GPT fails"""

    @staticmethod
    def extract_location(resume_text: str) -> str:
        """Fallback location extraction"""
        logger.warning("Using fallback location extraction")
        city_patterns = [
            ('manila', 'Manila, Philippines'),
            ('quezon city', 'Quezon City, Philippines'),
            ('davao', 'Davao City, Philippines'),
            ('cebu', 'Cebu City, Philippines'),
        ]

        text_lower = resume_text.lower()
        for pattern, city in city_patterns:
            if pattern in text_lower:
                return city
        return "Unknown"

    @staticmethod
    def extract_skills(resume_text: str) -> List[str]:
        """Fallback skill extraction"""
        logger.warning("Using fallback skill extraction")
        skill_keywords = [
            'autocad', 'sketchup', 'revit', 'excel', 'python',
            'sql', 'photoshop', 'canva', 'project management'
        ]

        skills = []
        text_lower = resume_text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                skills.append(skill.title())
        return skills

    @staticmethod
    def extract_work_experience(gpt_company: str) -> Dict[str, Any]:
        """Fallback work experience extraction"""
        logger.warning("Using fallback work experience extraction")
        return {
            "entries": []
        }


# ============================================================================
# BATCH REQUEST GENERATION
# ============================================================================

def create_extraction_prompt(resume_text: str, gpt_company: str) -> str:
    """Create a single prompt to extract all data"""
    prompt = f"""Extract the following information from this resume and work history:

RESUME:
{resume_text[:2500]}

WORK HISTORY:
{gpt_company[:2000]}

Extract and return as valid JSON:
{{
  "location": "City, Country (e.g., 'Manila, Philippines' or 'Unknown' if not found)",
  "skills": ["skill1", "skill2", "skill3"],
  "work_experience": {{
    "entries": [
      {{
        "company": "Company Name",
        "start_date": "Jan 2020",
        "end_date": "Jun 2023",
        "years": 3.5
      }}
    ]
  }}
}}

Instructions:
- Location: Current city and country from resume
- Skills: ALL technical skills, software, certifications
- Work Experience: Parse all jobs with company, dates, years

Return ONLY valid JSON, no additional text."""

    return prompt


def generate_batch_requests(
    csv_file: str,
    output_file: str,
    start_idx: int = 0,
    max_records: Optional[int] = None
) -> int:
    """
    Generate JSONL file for OpenAI Batch API with error handling.
    """
    logger.info("=" * 80)
    logger.info("GENERATING BATCH REQUESTS")
    logger.info("=" * 80)

    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    requests = []
    errors = 0

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                try:
                    # Skip already processed
                    if i < start_idx:
                        continue

                    # Check max limit
                    if max_records and len(requests) >= max_records:
                        break

                    resume_text = row.get("Resume TXT", "")
                    gpt_company = row.get("GPT COMPANY", "")
                    applicant_id = row.get("Applicant ID", str(i))

                    # Skip empty records
                    if not resume_text and not gpt_company:
                        logger.warning(f"Skipping empty record: {applicant_id}")
                        continue

                    # Create batch request
                    request = {
                        "custom_id": f"applicant_{applicant_id}",
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": config.openai_model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a precise data extraction assistant. Return ONLY valid JSON."
                                },
                                {
                                    "role": "user",
                                    "content": create_extraction_prompt(resume_text, gpt_company)
                                }
                            ],
                            "temperature": 0,
                            "max_tokens": 800,
                            "response_format": {"type": "json_object"}
                        }
                    }

                    requests.append(request)

                    if len(requests) % 500 == 0:
                        logger.info(f"Generated {len(requests)} requests...")

                except Exception as e:
                    logger.error(f"Error processing row {i}: {e}")
                    errors += 1
                    continue

    except Exception as e:
        logger.error(f"Fatal error reading CSV: {e}")
        raise

    # Write to JSONL
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')

        logger.info(f"✓ Generated {len(requests)} batch requests")
        logger.info(f"✓ Saved to: {output_file}")
        if errors > 0:
            logger.warning(f"⚠ {errors} errors during generation")

    except Exception as e:
        logger.error(f"Error writing JSONL: {e}")
        raise

    return len(requests)


# ============================================================================
# BATCH SUBMISSION WITH ERROR HANDLING
# ============================================================================

def submit_batch_job(
    jsonl_file: str,
    description: str = "Applicant data extraction"
) -> Optional[Dict]:
    """Submit batch job with retry logic"""

    logger.info("=" * 80)
    logger.info("SUBMITTING BATCH JOB")
    logger.info("=" * 80)

    if not os.path.exists(jsonl_file):
        logger.error(f"JSONL file not found: {jsonl_file}")
        raise FileNotFoundError(f"JSONL file not found: {jsonl_file}")

    client = OpenAI(
        api_key=config.openai_api_key,
        timeout=30.0  # 30 second timeout
    )

    for attempt in range(config.max_retries):
        try:
            # Upload file
            logger.info(f"[Attempt {attempt + 1}/{config.max_retries}] Uploading {jsonl_file}...")

            with open(jsonl_file, 'rb') as f:
                batch_file = client.files.create(
                    file=f,
                    purpose="batch"
                )

            logger.info(f"✓ File uploaded: {batch_file.id}")

            # Create batch
            logger.info("Creating batch job...")
            batch = client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"description": description}
            )

            logger.info(f"✓ Batch job created: {batch.id}")
            logger.info(f"Status: {batch.status}")

            # Save batch ID
            with open("batch_job_id.txt", "w") as f:
                f.write(batch.id)

            return {
                "batch_id": batch.id,
                "status": batch.status,
                "file_id": batch_file.id
            }

        except APITimeoutError:
            logger.error(f"Timeout on attempt {attempt + 1}")
            if attempt < config.max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

        except RateLimitError:
            logger.error(f"Rate limit hit on attempt {attempt + 1}")
            if attempt < config.max_retries - 1:
                time.sleep(10)
            else:
                raise

        except APIError as e:
            logger.error(f"API error: {e}")
            raise

    return None


# ============================================================================
# BATCH STATUS CHECK
# ============================================================================

def check_batch_status(batch_id: str) -> Optional[Dict]:
    """Check batch status with error handling"""

    client = OpenAI(api_key=config.openai_api_key, timeout=30.0)

    try:
        batch = client.batches.retrieve(batch_id)

        logger.info("=" * 80)
        logger.info(f"BATCH STATUS: {batch_id}")
        logger.info("=" * 80)
        logger.info(f"Status: {batch.status}")
        logger.info(f"Created: {datetime.fromtimestamp(batch.created_at)}")
        logger.info(f"Progress: {batch.request_counts}")

        if batch.status == "completed":
            logger.info(f"✓ BATCH COMPLETED!")
            logger.info(f"Output file ID: {batch.output_file_id}")
        elif batch.status == "failed":
            logger.error(f"✗ BATCH FAILED")
            if batch.error_file_id:
                logger.error(f"Error file ID: {batch.error_file_id}")
        else:
            logger.info(f"⏳ Batch still processing...")

        logger.info("=" * 80)

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "output_file_id": getattr(batch, 'output_file_id', None),
            "request_counts": batch.request_counts
        }

    except Exception as e:
        logger.error(f"Error checking batch status: {e}")
        return None


# ============================================================================
# DOWNLOAD RESULTS
# ============================================================================

def download_batch_results(
    batch_id: str,
    output_file: str = "batch_results.jsonl"
) -> Optional[str]:
    """Download batch results with error handling"""

    client = OpenAI(api_key=config.openai_api_key, timeout=60.0)

    try:
        batch = client.batches.retrieve(batch_id)

        if batch.status != "completed":
            logger.error(f"Batch not completed. Status: {batch.status}")
            return None

        logger.info("=" * 80)
        logger.info("DOWNLOADING BATCH RESULTS")
        logger.info("=" * 80)

        # Download output
        logger.info("Downloading results...")
        file_response = client.files.content(batch.output_file_id)

        # Save to file
        with open(output_file, 'wb') as f:
            f.write(file_response.content)

        logger.info(f"✓ Results saved to: {output_file}")
        return output_file

    except Exception as e:
        logger.error(f"Error downloading results: {e}")
        return None


# ============================================================================
# PROCESS RESULTS WITH VALIDATION
# ============================================================================

def process_batch_results(
    results_file: str,
    original_csv: str,
    output_json: str
) -> List[ApplicantRecord]:
    """Process and validate batch results"""

    logger.info("=" * 80)
    logger.info("PROCESSING BATCH RESULTS")
    logger.info("=" * 80)

    fallback_extractor = FallbackExtractor()
    results_map = {}
    parse_errors = 0

    # Load batch results
    logger.info(f"[1/3] Loading batch results from {results_file}...")

    try:
        with open(results_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    result = json.loads(line)
                    custom_id = result["custom_id"]

                    response_content = result["response"]["body"]["choices"][0]["message"]["content"]
                    extracted_data = json.loads(response_content)

                    # Validate with Pydantic
                    validated_data = ExtractedData(**extracted_data)
                    results_map[custom_id] = validated_data.dict()

                except ValidationError as e:
                    logger.warning(f"Validation error at line {line_num}: {e}")
                    parse_errors += 1
                except Exception as e:
                    logger.warning(f"Failed to parse line {line_num}: {e}")
                    parse_errors += 1
                    continue

        logger.info(f"✓ Loaded {len(results_map)} successful extractions")
        if parse_errors > 0:
            logger.warning(f"⚠ {parse_errors} parsing errors (will use fallback)")

    except Exception as e:
        logger.error(f"Error loading results: {e}")
        raise

    # Load original CSV and merge
    logger.info(f"[2/3] Loading original data from {original_csv}...")
    processed_records = []
    fallback_count = 0

    try:
        with open(original_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                try:
                    applicant_id = row.get("Applicant ID", str(i))
                    custom_id = f"applicant_{applicant_id}"

                    # Get extracted data or use fallback
                    if custom_id in results_map:
                        extracted = results_map[custom_id]
                    else:
                        logger.warning(f"Using fallback for {applicant_id}")
                        extracted = {
                            "location": fallback_extractor.extract_location(row.get("Resume TXT", "")),
                            "skills": fallback_extractor.extract_skills(row.get("Resume TXT", "")),
                            "work_experience": fallback_extractor.extract_work_experience(row.get("GPT COMPANY", ""))
                        }
                        fallback_count += 1

                    # Process work experience safely
                    work_exp = extracted.get("work_experience", {})
                    entries = work_exp.get("entries", []) if work_exp else []

                    def safe_float(val):
                        try:
                            return float(val) if val else 0.0
                        except:
                            return 0.0

                    total_years = sum(safe_float(e.get("years", 0)) for e in entries if isinstance(e, dict))
                    longest_tenure = max([safe_float(e.get("years", 0)) for e in entries if isinstance(e, dict)], default=0.0)
                    current_company = entries[0].get("company", "") if entries and isinstance(entries[0], dict) else ""
                    company_names = [e.get("company", "") for e in entries if isinstance(e, dict) and e.get("company")]

                    # Normalize education
                    edu_raw = row.get("Education", "")
                    if "bachelor" in edu_raw.lower() or "bs" in edu_raw.lower():
                        education_level = "Bachelor's Degree"
                    elif "master" in edu_raw.lower() or "ms" in edu_raw.lower():
                        education_level = "Master's Degree"
                    else:
                        education_level = edu_raw if edu_raw else "Not Specified"

                    # Parse date
                    try:
                        date_str = row.get("Date applied", "")
                        dt = datetime.strptime(date_str, "%m/%d/%Y")
                        date_applied = int(dt.timestamp())
                    except:
                        date_applied = int(datetime.now().timestamp())

                    # Create and validate record
                    record = ApplicantRecord(
                        id=applicant_id,
                        full_name=row.get("Full Name", ""),
                        email=row.get("First name", "unknown") + "@example.com",
                        job_title=row.get("Job Title (from JOB #)", ""),
                        current_stage=row.get("Current stage", "Applied"),
                        education_level=education_level,
                        education_raw=edu_raw,
                        total_years_experience=total_years,
                        longest_tenure_years=longest_tenure,
                        current_company=current_company,
                        work_history_text=row.get("GPT COMPANY", ""),
                        company_names=", ".join(company_names),
                        skills_extracted=", ".join(extracted.get("skills", [])),
                        skills_raw_text="",
                        resume_full_text=row.get("Resume TXT", ""),
                        tasks_summary=row.get("GPT TASKS", ""),
                        location=extracted.get("location", "Unknown"),
                        date_applied=date_applied,
                        resume_url=row.get("PDF_RESUME_DO_URL", "")
                    )

                    processed_records.append(record.dict())

                except ValidationError as e:
                    logger.error(f"Validation error for record {i}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing record {i}: {e}")
                    continue

        logger.info(f"✓ Processed {len(processed_records)} records")
        if fallback_count > 0:
            logger.warning(f"⚠ Used fallback extraction for {fallback_count} records")

    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        raise

    # Save to JSON
    logger.info(f"[3/3] Saving to {output_json}...")

    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(processed_records, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved!")
        logger.info("=" * 80)
        logger.info("✓ BATCH PROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Final output: {output_json}")
        logger.info(f"Total records: {len(processed_records)}")

    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        raise

    return processed_records


# ============================================================================
# MAIN CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Production batch processing with full error handling")
    parser.add_argument("--generate", action="store_true", help="Generate batch requests")
    parser.add_argument("--submit", action="store_true", help="Submit batch job")
    parser.add_argument("--check", type=str, help="Check batch status")
    parser.add_argument("--download", type=str, help="Download batch results")
    parser.add_argument("--process", type=str, help="Process batch results")
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("--max", type=int, help="Max records to process")

    args = parser.parse_args()

    # Paths
    CSV_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/raw/test_fixed.csv"
    BATCH_REQUESTS_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/batch_requests.jsonl"
    BATCH_RESULTS_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/batch_results.jsonl"
    OUTPUT_JSON = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/preprocessed_with_gpt_batch.json"

    try:
        if args.generate:
            generate_batch_requests(CSV_FILE, BATCH_REQUESTS_FILE, args.start, args.max)

        elif args.submit:
            submit_batch_job(BATCH_REQUESTS_FILE)

        elif args.check:
            check_batch_status(args.check)

        elif args.download:
            download_batch_results(args.download, BATCH_RESULTS_FILE)

        elif args.process:
            process_batch_results(args.process, CSV_FILE, OUTPUT_JSON)

        else:
            print("Production Batch Processing")
            print("=" * 80)
            print("1. Generate:  python3 scripts/batch_preprocess_gpt_prod.py --generate")
            print("2. Submit:    python3 scripts/batch_preprocess_gpt_prod.py --submit")
            print("3. Check:     python3 scripts/batch_preprocess_gpt_prod.py --check <batch_id>")
            print("4. Download:  python3 scripts/batch_preprocess_gpt_prod.py --download <batch_id>")
            print("5. Process:   python3 scripts/batch_preprocess_gpt_prod.py --process batch_results.jsonl")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
