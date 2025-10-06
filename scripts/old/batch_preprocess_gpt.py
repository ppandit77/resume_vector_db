"""
Batch Processing for Applicant Data Extraction
Uses OpenAI Batch API for 50% cost savings and efficient processing
Combines location, skills, and work experience into single API call
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI

# Load environment
import sys
sys.path.append(os.path.dirname(__file__))
from load_env import load_env
load_env()


# ============================================================================
# BATCH REQUEST GENERATION
# ============================================================================

def create_extraction_prompt(resume_text: str, gpt_company: str) -> str:
    """
    Create a single prompt to extract location, skills, and work experience.
    """
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
- Skills: ALL technical skills, software (AutoCAD, Excel, Python, etc.), certifications, professional competencies
- Work Experience: Parse all jobs with company name, dates, and calculated years of experience

Return ONLY valid JSON, no additional text."""

    return prompt


def generate_batch_requests(csv_file: str, output_file: str, start_idx: int = 0, max_records: int = None):
    """
    Generate JSONL file for OpenAI Batch API.

    Args:
        csv_file: Input CSV with applicant data
        output_file: Output JSONL file for batch requests
        start_idx: Start from this record (for resuming)
        max_records: Maximum records to process (None = all)
    """
    print("=" * 80)
    print("GENERATING BATCH REQUESTS")
    print("=" * 80)

    requests = []

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            # Skip already processed records
            if i < start_idx:
                continue

            # Check max limit
            if max_records and len(requests) >= max_records:
                break

            resume_text = row.get("Resume TXT", "")
            gpt_company = row.get("GPT COMPANY", "")
            applicant_id = row.get("Applicant ID", str(i))

            # Skip if no content
            if not resume_text and not gpt_company:
                continue

            # Create batch request
            request = {
                "custom_id": f"applicant_{applicant_id}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a precise data extraction assistant. Extract information and return ONLY valid JSON."
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

            if (len(requests)) % 500 == 0:
                print(f"  Generated {len(requests)} requests...")

    # Write to JSONL
    with open(output_file, 'w', encoding='utf-8') as f:
        for req in requests:
            f.write(json.dumps(req) + '\n')

    print(f"\n✓ Generated {len(requests)} batch requests")
    print(f"✓ Saved to: {output_file}")
    print(f"\nNext step: Upload this file to OpenAI Batch API")

    return len(requests)


# ============================================================================
# BATCH SUBMISSION
# ============================================================================

def submit_batch_job(jsonl_file: str, description: str = "Applicant data extraction"):
    """
    Submit batch job to OpenAI.

    Args:
        jsonl_file: Path to JSONL file with requests
        description: Description for the batch job

    Returns:
        Batch job object
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print("\n" + "=" * 80)
    print("SUBMITTING BATCH JOB")
    print("=" * 80)

    # Upload file
    print(f"\n[1/2] Uploading {jsonl_file}...")
    with open(jsonl_file, 'rb') as f:
        batch_file = client.files.create(
            file=f,
            purpose="batch"
        )

    print(f"✓ File uploaded: {batch_file.id}")

    # Create batch
    print(f"\n[2/2] Creating batch job...")
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": description
        }
    )

    print(f"✓ Batch job created!")
    print(f"\n{'=' * 80}")
    print(f"Batch ID: {batch.id}")
    print(f"Status: {batch.status}")
    print(f"Total requests: {batch.request_counts}")
    print(f"{'=' * 80}")
    print(f"\nCheck status with:")
    print(f"  python3 scripts/batch_preprocess_gpt.py --check {batch.id}")

    # Save batch ID for reference
    with open("batch_job_id.txt", "w") as f:
        f.write(batch.id)

    return batch


def check_batch_status(batch_id: str):
    """
    Check the status of a batch job.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    batch = client.batches.retrieve(batch_id)

    print("\n" + "=" * 80)
    print(f"BATCH STATUS: {batch_id}")
    print("=" * 80)
    print(f"Status: {batch.status}")
    print(f"Created: {datetime.fromtimestamp(batch.created_at)}")
    print(f"Progress: {batch.request_counts}")

    if batch.status == "completed":
        print(f"\n✓ BATCH COMPLETED!")
        print(f"Output file ID: {batch.output_file_id}")
        print(f"\nDownload results with:")
        print(f"  python3 scripts/batch_preprocess_gpt.py --download {batch_id}")
    elif batch.status == "failed":
        print(f"\n✗ BATCH FAILED")
        print(f"Error file ID: {batch.error_file_id}")
    else:
        print(f"\n⏳ Batch is still processing...")
        print(f"Check again later (typically completes within 24 hours)")

    print("=" * 80)

    return batch


def download_batch_results(batch_id: str, output_file: str = "batch_results.jsonl"):
    """
    Download and save batch results.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        print(f"✗ Batch not completed yet. Status: {batch.status}")
        return None

    print("\n" + "=" * 80)
    print("DOWNLOADING BATCH RESULTS")
    print("=" * 80)

    # Download output file
    print(f"\nDownloading results...")
    file_response = client.files.content(batch.output_file_id)

    # Save to file
    with open(output_file, 'wb') as f:
        f.write(file_response.content)

    print(f"✓ Results saved to: {output_file}")
    print(f"\nProcess results with:")
    print(f"  python3 scripts/batch_preprocess_gpt.py --process {output_file}")

    return output_file


# ============================================================================
# PROCESS BATCH RESULTS
# ============================================================================

def process_batch_results(results_file: str, original_csv: str, output_json: str):
    """
    Process batch results and merge with original data.
    """
    print("\n" + "=" * 80)
    print("PROCESSING BATCH RESULTS")
    print("=" * 80)

    # Load batch results
    print(f"\n[1/3] Loading batch results from {results_file}...")
    results_map = {}

    with open(results_file, 'r') as f:
        for line in f:
            result = json.loads(line)
            custom_id = result["custom_id"]

            try:
                response_content = result["response"]["body"]["choices"][0]["message"]["content"]
                extracted_data = json.loads(response_content)
                results_map[custom_id] = extracted_data
            except Exception as e:
                print(f"  Warning: Failed to parse {custom_id}: {e}")
                continue

    print(f"✓ Loaded {len(results_map)} successful extractions")

    # Load original CSV
    print(f"\n[2/3] Loading original data from {original_csv}...")
    processed_records = []

    with open(original_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            applicant_id = row.get("Applicant ID", str(i))
            custom_id = f"applicant_{applicant_id}"

            # Get extracted data
            extracted = results_map.get(custom_id, {})

            # Process work experience
            work_exp = extracted.get("work_experience", {})
            entries = work_exp.get("entries", []) if work_exp else []

            # Safely convert years to float
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

            # Create record
            record = {
                "id": applicant_id,
                "full_name": row.get("Full Name", ""),
                "email": row.get("First name", "unknown") + "@example.com",
                "job_title": row.get("Job Title (from JOB #)", ""),
                "current_stage": row.get("Current stage", "Applied"),
                "education_level": education_level,
                "education_raw": edu_raw,
                "total_years_experience": total_years,
                "longest_tenure_years": longest_tenure,
                "current_company": current_company,
                "work_history_text": row.get("GPT COMPANY", ""),
                "company_names": ", ".join(company_names),
                "skills_extracted": ", ".join(extracted.get("skills", [])),
                "skills_raw_text": "",
                "resume_full_text": row.get("Resume TXT", ""),
                "tasks_summary": row.get("GPT TASKS", ""),
                "location": extracted.get("location", "Unknown"),
                "date_applied": date_applied,
                "resume_url": row.get("PDF_RESUME_DO_URL", "")
            }

            processed_records.append(record)

    print(f"✓ Processed {len(processed_records)} records")

    # Save to JSON
    print(f"\n[3/3] Saving to {output_json}...")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(processed_records, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved!")

    print("\n" + "=" * 80)
    print("✓ BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Final output: {output_json}")
    print(f"Total records: {len(processed_records)}")

    return processed_records


# ============================================================================
# MAIN CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch processing for applicant data extraction")
    parser.add_argument("--generate", action="store_true", help="Generate batch requests")
    parser.add_argument("--submit", action="store_true", help="Submit batch job")
    parser.add_argument("--check", type=str, help="Check batch status (provide batch ID)")
    parser.add_argument("--download", type=str, help="Download batch results (provide batch ID)")
    parser.add_argument("--process", type=str, help="Process batch results (provide results JSONL file)")
    parser.add_argument("--start", type=int, default=0, help="Start index for processing")
    parser.add_argument("--max", type=int, help="Maximum records to process")

    args = parser.parse_args()

    # Paths
    CSV_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/data/raw/test_fixed.csv"
    BATCH_REQUESTS_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/batch_requests.jsonl"
    BATCH_RESULTS_FILE = "/mnt/c/Users/prita/Downloads/SuperLinked/batch_results.jsonl"
    OUTPUT_JSON = "/mnt/c/Users/prita/Downloads/SuperLinked/data/processed/preprocessed_with_gpt_batch.json"

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
        print("Batch Processing Workflow:")
        print("=" * 80)
        print("1. Generate requests:  python3 scripts/batch_preprocess_gpt.py --generate")
        print("2. Submit batch:       python3 scripts/batch_preprocess_gpt.py --submit")
        print("3. Check status:       python3 scripts/batch_preprocess_gpt.py --check <batch_id>")
        print("4. Download results:   python3 scripts/batch_preprocess_gpt.py --download <batch_id>")
        print("5. Process results:    python3 scripts/batch_preprocess_gpt.py --process batch_results.jsonl")
