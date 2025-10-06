import re
import json
import csv
from datetime import datetime
from typing import List, Dict, Any
import os

# You'll need to install: pip install openai
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not installed. Install with: pip install openai")


# ============================================================================
# GPT-BASED EXTRACTION
# ============================================================================

class GPTExtractor:
    """
    Uses GPT-4o-mini for intelligent extraction of location, skills, and work experience.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize GPT extractor.

        Args:
            api_key: OpenAI API key. If None, will look for OPENAI_API_KEY env variable.
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package required. Install with: pip install openai")

        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"  # Cost-effective model for extraction

    def extract_location(self, resume_text: str, max_retries: int = 2) -> str:
        """
        Extract location from resume using GPT.

        Args:
            resume_text: Full resume text
            max_retries: Number of retries on failure

        Returns:
            Normalized location string (e.g., "Quezon City, Philippines")
        """
        if not resume_text or len(resume_text.strip()) < 10:
            return "Unknown"

        prompt = f"""Extract the candidate's current location/city from this resume.

Resume excerpt:
{resume_text[:1500]}

Return ONLY the city name in this format: "City, Country" (e.g., "Quezon City, Philippines" or "Manila, Philippines")
If location is unclear, return "Unknown"."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise data extraction assistant. Return only the requested information with no additional text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=50
            )

            location = response.choices[0].message.content.strip()
            return location if location else "Unknown"

        except Exception as e:
            print(f"Error extracting location: {e}")
            return "Unknown"

    def extract_skills(self, resume_text: str, max_retries: int = 2) -> List[str]:
        """
        Extract technical and professional skills from resume using GPT.

        Args:
            resume_text: Full resume text
            max_retries: Number of retries on failure

        Returns:
            List of skill strings
        """
        if not resume_text or len(resume_text.strip()) < 10:
            return []

        prompt = f"""Extract ALL technical skills, software proficiencies, and professional competencies from this resume.

Resume:
{resume_text[:2500]}

Return a comma-separated list of skills. Include:
- Software (AutoCAD, Excel, Python, etc.)
- Technologies (SQL, AWS, React, etc.)
- Certifications
- Professional skills (Project Management, etc.)

Format: skill1, skill2, skill3
Return "None" if no clear skills found."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise skill extraction assistant. Extract only real, verifiable skills mentioned in the text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200
            )

            skills_str = response.choices[0].message.content.strip()

            if skills_str.lower() == "none" or not skills_str:
                return []

            # Parse comma-separated skills
            skills = [s.strip() for s in skills_str.split(',') if s.strip()]
            return skills

        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []

    def extract_work_experience(self, gpt_company_text: str, resume_text: str = "") -> Dict[str, Any]:
        """
        Extract structured work experience from GPT COMPANY column and resume.

        Args:
            gpt_company_text: Pre-extracted company text from GPT COMPANY column
            resume_text: Full resume for additional context

        Returns:
            Dictionary with work experience details
        """
        if not gpt_company_text or len(gpt_company_text.strip()) < 5:
            return {
                "total_years": 0.0,
                "longest_tenure": 0.0,
                "current_company": "",
                "company_names": [],
                "entries": []
            }

        prompt = f"""Parse this work experience data into structured JSON.

Work History:
{gpt_company_text[:2000]}

Extract for EACH job:
1. Company name (clean, without location)
2. Start and end dates (or "Present")
3. Years of experience (calculate if needed)

Return JSON in this format:
{{
  "entries": [
    {{
      "company": "Company Name",
      "start_date": "Jan 2020",
      "end_date": "Jun 2025",
      "years": 5.5
    }}
  ]
}}

If you cannot parse, return: {{"entries": []}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise work experience parser. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            entries = result.get("entries", [])

            # Calculate aggregate stats
            total_years = sum(e.get("years", 0) for e in entries)
            longest_tenure = max([e.get("years", 0) for e in entries], default=0.0)
            current_company = entries[0].get("company", "") if entries else ""
            company_names = [e.get("company", "") for e in entries if e.get("company")]

            return {
                "total_years": total_years,
                "longest_tenure": longest_tenure,
                "current_company": current_company,
                "company_names": company_names,
                "entries": entries
            }

        except Exception as e:
            print(f"Error extracting work experience: {e}")
            # Fallback to rule-based parsing
            return self._fallback_parse_experience(gpt_company_text)

    def _fallback_parse_experience(self, work_exp_string: str) -> Dict[str, Any]:
        """Fallback rule-based parser if GPT fails."""
        if not work_exp_string or work_exp_string.strip() == "":
            return {
                "total_years": 0.0,
                "longest_tenure": 0.0,
                "current_company": "",
                "company_names": [],
                "entries": []
            }

        entries = []
        company_names = []

        parts = re.split(r'\)\s*,\s*', work_exp_string)

        for part in parts:
            if not part.strip():
                continue

            if not part.endswith(')'):
                part += ')'

            match = re.match(r'(.+?)\s*\((.+?),\s*(\d+\.?\d*)\s*years?\)', part)

            if match:
                company_loc, dates, years = match.groups()
                years_float = float(years)
                company = re.split(r'\s*[-–]\s*', company_loc)[0].strip()

                entries.append({
                    "company": company,
                    "start_date": dates.split(" to ")[0].strip() if " to " in dates else dates,
                    "end_date": dates.split(" to ")[1].strip() if " to " in dates else "Present",
                    "years": years_float
                })

                company_names.append(company)

        total_years = sum(entry["years"] for entry in entries)
        longest_tenure = max([entry["years"] for entry in entries], default=0.0)
        current_company = entries[0]["company"] if entries else ""

        return {
            "total_years": total_years,
            "longest_tenure": longest_tenure,
            "current_company": current_company,
            "company_names": company_names,
            "entries": entries
        }


# ============================================================================
# FALLBACK EXTRACTORS (when GPT not available)
# ============================================================================

def extract_location_fallback(resume_text: str) -> str:
    """Rule-based location extraction."""
    city_patterns = [
        ('quezon city', 'Quezon City'), ('davao city', 'Davao City'),
        ('manila city', 'Manila City'), ('cebu city', 'Cebu City'),
        ('cagayan de oro', 'Cagayan de Oro'),
        ('davao', 'Davao'), ('manila', 'Manila'), ('cebu', 'Cebu'),
        ('iloilo', 'Iloilo'), ('bacolod', 'Bacolod'), ('cagayan', 'Cagayan'),
        ('batangas', 'Batangas'), ('quezon', 'Quezon'), ('makati', 'Makati'),
        ('taguig', 'Taguig'), ('pasig', 'Pasig')
    ]

    text_lower = resume_text.lower()
    for pattern, city_name in city_patterns:
        if pattern in text_lower:
            return city_name + ", Philippines"

    return "Unknown"


def extract_skills_fallback(resume_text: str) -> List[str]:
    """Rule-based skill extraction."""
    skill_keywords = [
        'autocad', 'sketchup', 'revit', 'microsoft office', 'excel', 'word',
        'photoshop', 'canva', 'd5 render', 'cad', 'staad', 'etabs', 'sap',
        'primavera', 'ms project', 'python', 'java', 'sql', 'arcgis'
    ]

    skills_found = set()
    text_lower = resume_text.lower()

    for skill in skill_keywords:
        if skill in text_lower:
            skills_found.add(skill.title())

    # Deduplicate
    if "Autocad" in skills_found and "Cad" in skills_found:
        skills_found.remove("Cad")

    return sorted(list(skills_found))


# ============================================================================
# PREPROCESSING FUNCTION
# ============================================================================

def preprocess_applicant_data(row: Dict[str, str], gpt_extractor: GPTExtractor = None) -> Dict[str, Any]:
    """
    Preprocess applicant data with optional GPT-based extraction.

    Args:
        row: Raw CSV row
        gpt_extractor: Optional GPTExtractor instance. If None, uses rule-based fallbacks.
    """
    def safe_get(key, default=""):
        value = row.get(key, default)
        return value if value is not None else default

    resume_text = safe_get("Resume TXT")
    gpt_company = safe_get("GPT COMPANY")

    # Extract using GPT or fallback
    if gpt_extractor:
        location = gpt_extractor.extract_location(resume_text)
        skills = gpt_extractor.extract_skills(resume_text)
        work_exp = gpt_extractor.extract_work_experience(gpt_company, resume_text)
    else:
        location = extract_location_fallback(resume_text)
        skills = extract_skills_fallback(resume_text)
        # Use fallback parser
        work_exp = GPTExtractor(api_key="dummy")._fallback_parse_experience(gpt_company)

    # Normalize education
    edu_raw = safe_get("Education")
    if "bachelor" in edu_raw.lower() or "bs" in edu_raw.lower():
        education_level = "Bachelor's Degree"
    elif "master" in edu_raw.lower() or "ms" in edu_raw.lower():
        education_level = "Master's Degree"
    else:
        education_level = edu_raw if edu_raw else "Not Specified"

    # Parse date
    try:
        date_str = safe_get("Date applied")
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        date_applied = int(dt.timestamp())
    except:
        date_applied = int(datetime.now().timestamp())

    # Create email
    first_name = safe_get("First name")
    email = first_name + "@example.com" if first_name else "unknown@example.com"

    return {
        "id": safe_get("Applicant ID"),
        "full_name": safe_get("Full Name"),
        "email": email,
        "job_title": safe_get("Job Title (from JOB #)"),
        "current_stage": safe_get("Current stage", "Applied"),
        "education_level": education_level,
        "education_raw": edu_raw,
        "total_years_experience": work_exp["total_years"],
        "longest_tenure_years": work_exp["longest_tenure"],
        "current_company": work_exp["current_company"],
        "work_history_text": gpt_company,
        "company_names": ", ".join(work_exp["company_names"]),
        "skills_extracted": ", ".join(skills),
        "skills_raw_text": "",
        "resume_full_text": resume_text,
        "tasks_summary": safe_get("GPT TASKS"),
        "location": location,
        "date_applied": date_applied,
        "resume_url": safe_get("PDF_RESUME_DO_URL")
    }


# ============================================================================
# BATCH PROCESSING WITH PROGRESS
# ============================================================================

def process_csv_with_gpt(
    input_file: str,
    output_file: str,
    api_key: str = None,
    use_gpt: bool = True,
    sample_size: int = 10,
    batch_size: int = 100
):
    """
    Process CSV with GPT-based extraction and progress tracking.

    Args:
        input_file: Input CSV path
        output_file: Output JSON path
        api_key: OpenAI API key
        use_gpt: Whether to use GPT (False = rule-based fallback)
        sample_size: Number of records to display
        batch_size: Save checkpoint every N records
    """
    # Initialize extractor
    gpt_extractor = None
    if use_gpt:
        try:
            gpt_extractor = GPTExtractor(api_key=api_key)
            print("✓ GPT extractor initialized")
        except Exception as e:
            print(f"⚠ Could not initialize GPT: {e}")
            print("→ Falling back to rule-based extraction")

    processed_records = []

    print(f"\nProcessing {input_file}...")
    print("=" * 80)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            try:
                processed = preprocess_applicant_data(row, gpt_extractor)
                processed_records.append(processed)

                # Show samples
                if i < sample_size:
                    print(f"\n[{i+1}] {processed['full_name']}")
                    print(f"  📍 Location: {processed['location']}")
                    print(f"  💼 Experience: {processed['total_years_experience']:.1f} yrs @ {processed['current_company']}")
                    print(f"  🛠  Skills: {processed['skills_extracted'][:80]}...")

                # Save checkpoint
                if (i + 1) % batch_size == 0:
                    with open(output_file, 'w', encoding='utf-8') as out:
                        json.dump(processed_records, out, indent=2)
                    print(f"\n💾 Checkpoint: {i+1} records saved")

            except Exception as e:
                print(f"\n❌ Error at row {i+1}: {e}")
                continue

    # Final save
    print(f"\n{'=' * 80}")
    print(f"Saving {len(processed_records)} records to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_records, f, indent=2, ensure_ascii=False)

    print(f"✓ Processing complete: {len(processed_records)} records")

    return processed_records


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Load environment variables from .env file
    from load_env import load_env
    load_env()

    # Configuration
    INPUT_CSV = "/mnt/c/Users/prita/Downloads/SuperLinked/test_fixed.csv"
    OUTPUT_JSON = "/mnt/c/Users/prita/Downloads/SuperLinked/preprocessed_with_gpt.json"

    # Get API key from environment
    API_KEY = os.getenv("OPENAI_API_KEY")

    # Run with GPT (set to False for rule-based only)
    USE_GPT = True

    if USE_GPT and not API_KEY:
        print("⚠ Warning: OPENAI_API_KEY not set!")
        print("→ Please add your API key to .env file")
        print("→ Edit: /mnt/c/Users/prita/Downloads/SuperLinked/.env")
        print("\n→ Proceeding with rule-based extraction instead...")
        USE_GPT = False

    processed_data = process_csv_with_gpt(
        input_file=INPUT_CSV,
        output_file=OUTPUT_JSON,
        api_key=API_KEY,
        use_gpt=USE_GPT,
        sample_size=5,
        batch_size=100
    )

    print(f"\n{'=' * 80}")
    print("✓ COMPLETE")
    print(f"Output: {OUTPUT_JSON}")
    print(f"Records: {len(processed_data)}")