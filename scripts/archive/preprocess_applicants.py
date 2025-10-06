import re
import json
from datetime import datetime
from typing import List, Dict, Any
from superlinked import framework as sl

# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

@sl.schema
class Applicant:
    # Core identifiers
    id: sl.IdField
    full_name: sl.String
    email: sl.String

    # Job-related
    job_title: sl.String  # The position they applied for
    current_stage: sl.String  # Applied, Rejected, Interview, etc.

    # Education
    education_level: sl.String  # Normalized: Bachelor's, Master's, etc.
    education_raw: sl.String  # Raw education text

    # Experience
    total_years_experience: sl.Float
    longest_tenure_years: sl.Float  # Longest time at a single company
    current_company: sl.String
    work_history_text: sl.String  # Full work history for semantic search
    company_names: sl.String  # Comma-separated company names

    # Skills
    skills_extracted: sl.String  # Normalized, comma-separated skills
    skills_raw_text: sl.String  # Raw skills section from resume
    resume_full_text: sl.String  # Full resume for deep semantic search

    # Tasks/Responsibilities
    tasks_summary: sl.String  # GPT-extracted tasks

    # Location
    location: sl.String  # City/Region extracted

    # Temporal
    date_applied: sl.Timestamp

    # Documents
    resume_url: sl.String


# ============================================================================
# PREPROCESSING FUNCTIONS
# ============================================================================

def parse_work_experience(work_exp_string: str) -> Dict[str, Any]:
    """
    Parse work experience string into structured data.

    Example input:
    "National Housing Authority-Davao City (January 2020 to June 2025, 5.5 years),
     Apeiron Construction Solutions-Davao City (June 2019 to December 2019, 0.5 years)"
    """
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

    # Split by closing parenthesis followed by comma and optional space
    parts = re.split(r'\)\s*,\s*', work_exp_string)

    for part in parts:
        if not part.strip():
            continue

        # Add back the closing parenthesis if it was split
        if not part.endswith(')'):
            part += ')'

        # Pattern: Company-Location (Date to Date, X.Y years)
        match = re.match(r'(.+?)\s*\((.+?),\s*(\d+\.?\d*)\s*years?\)', part)

        if match:
            company_loc, dates, years = match.groups()
            years_float = float(years)

            # Extract company name (remove location after dash/hyphen)
            company = re.split(r'\s*[-–]\s*', company_loc)[0].strip()

            entries.append({
                "company": company,
                "full_text": company_loc.strip(),
                "dates": dates.strip(),
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


def extract_skills(resume_text: str, skills_section: str = None) -> Dict[str, Any]:
    """
    Extract and normalize skills from resume.
    """
    # Common skill patterns to look for
    skill_keywords = [
        'autocad', 'sketchup', 'revit', 'microsoft office', 'excel', 'word',
        'photoshop', 'canva', 'd5 render', 'cad', 'staad', 'etabs', 'sap',
        'primavera', 'ms project', 'python', 'java', 'sql', 'arcgis'
    ]

    skills_found = set()
    text_to_search = (resume_text + " " + (skills_section or "")).lower()

    for skill in skill_keywords:
        if skill in text_to_search:
            skills_found.add(skill.title())

    # Also extract from bullet points in skills section
    if skills_section:
        # Match lines starting with - or bullet points
        skill_lines = re.findall(r'[-•]\s*([^\n]+)', skills_section)
        for line in skill_lines:
            skills_found.add(line.strip())

    # Deduplicate: Remove "Cad" if "Autocad" is present
    if "Autocad" in skills_found and "Cad" in skills_found:
        skills_found.remove("Cad")

    return {
        "extracted": list(skills_found),
        "extracted_string": ", ".join(sorted(skills_found)),
        "raw": skills_section or ""
    }


def extract_location(resume_text: str, full_name: str) -> str:
    """
    Extract city/location from resume text.
    """
    # Common Philippine cities - check full names first, then abbreviations
    city_patterns = [
        ('quezon city', 'Quezon City'),
        ('davao city', 'Davao City'),
        ('manila city', 'Manila City'),
        ('cebu city', 'Cebu City'),
        ('cagayan de oro', 'Cagayan de Oro'),
        ('davao', 'Davao'),
        ('manila', 'Manila'),
        ('cebu', 'Cebu'),
        ('iloilo', 'Iloilo'),
        ('bacolod', 'Bacolod'),
        ('cagayan', 'Cagayan'),
        ('batangas', 'Batangas'),
        ('quezon', 'Quezon'),
        ('makati', 'Makati'),
        ('taguig', 'Taguig'),
        ('pasig', 'Pasig')
    ]

    text_lower = resume_text.lower()

    # Check patterns in order (longer/specific names first)
    for pattern, city_name in city_patterns:
        if pattern in text_lower:
            return city_name

    # Try to find any "City" pattern as fallback
    city_match = re.search(r'([A-Z][a-z]+\s+City)', resume_text)
    if city_match:
        return city_match.group(1)

    return "Unknown"


def normalize_education(education_raw: str) -> str:
    """
    Normalize education level.
    """
    if not education_raw:
        return "Not Specified"

    edu_lower = education_raw.lower()

    if "master" in edu_lower or "ms" in edu_lower or "m.s." in edu_lower:
        return "Master's Degree"
    elif "bachelor" in edu_lower or "bs" in edu_lower or "b.s." in edu_lower:
        return "Bachelor's Degree"
    elif "undergraduate" in edu_lower or "didn't finish" in edu_lower:
        return "Bachelor's (Incomplete)"
    elif "diploma" in edu_lower or "vocational" in edu_lower:
        return "Diploma/Vocational"
    elif "phd" in edu_lower or "doctorate" in edu_lower:
        return "Doctorate"
    else:
        return education_raw


def parse_date_applied(date_string: str) -> int:
    """
    Convert date string to Unix timestamp.
    Format: "9/22/2025" -> timestamp
    """
    try:
        dt = datetime.strptime(date_string, "%m/%d/%Y")
        return int(dt.timestamp())
    except:
        return int(datetime.now().timestamp())


# ============================================================================
# DATA PREPROCESSING PIPELINE
# ============================================================================

def preprocess_applicant_data(row: Dict[str, str]) -> Dict[str, Any]:
    """
    Convert raw TSV row into Superlinked-compatible format.

    Args:
        row: Dictionary with keys from your TSV (Full Name, Applicant ID, etc.)

    Returns:
        Dictionary formatted for Superlinked ingestion
    """
    # Helper to safely get values and convert None to empty string
    def safe_get(key, default=""):
        value = row.get(key, default)
        return value if value is not None else default

    # Parse work experience
    work_exp = parse_work_experience(safe_get("GPT COMPANY"))

    # Extract skills
    skills = extract_skills(
        resume_text=safe_get("Resume TXT"),
        skills_section=None  # Could extract from resume if structured
    )

    # Extract location
    location = extract_location(
        resume_text=safe_get("Resume TXT"),
        full_name=safe_get("Full Name")
    )

    # Parse date
    date_applied = parse_date_applied(safe_get("Date applied"))

    # Normalize education
    education_level = normalize_education(safe_get("Education"))

    # Create email from first name
    first_name = safe_get("First name")
    email = first_name + "@example.com" if first_name else "unknown@example.com"

    return {
        "id": safe_get("Applicant ID"),
        "full_name": safe_get("Full Name"),
        "email": email,
        "job_title": safe_get("Job Title (from JOB #)"),
        "current_stage": safe_get("Current stage", "Applied"),
        "education_level": education_level,
        "education_raw": safe_get("Education"),
        "total_years_experience": work_exp["total_years"],
        "longest_tenure_years": work_exp["longest_tenure"],
        "current_company": work_exp["current_company"],
        "work_history_text": safe_get("GPT COMPANY"),
        "company_names": ", ".join(work_exp["company_names"]),
        "skills_extracted": skills["extracted_string"],
        "skills_raw_text": skills["raw"],
        "resume_full_text": safe_get("Resume TXT"),
        "tasks_summary": safe_get("GPT TASKS"),
        "location": location,
        "date_applied": date_applied,
        "resume_url": safe_get("PDF_RESUME_DO_URL")
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example raw data (from your TSV)
    raw_data = {
        "Full Name": "Axel Arvin Alcanzar - AutoCAD Drafter",
        "Applicant ID": "26142144",
        "Current stage": "Rejected",
        "First name": "Axel Arvin",
        "Last name": "Alcanzar",
        "Education": "Bachelor's Degree",
        "Date applied": "9/22/2025",
        "PDF_RESUME_DO_URL": "https://nightowl-bucket.sfo3.digitaloceanspaces.com/...",
        "Job Title (from JOB #)": "AutoCAD Drafter",
        "GPT COMPANY": "National Housing Authority-Davao City (January 2020 to June 2025, 5.5 years), Apeiron Construction Solutions-Davao City (June 2019 to December 2019, 0.5 years)",
        "GPT TASKS": "Monitor and ensure quality of land development and housing construction during project implementation, Communicate with the Contractor/Developer...",
        "Resume TXT": "Axel Arvin Alcanzar\n\nFast learner and very eager to learn new things\n\nDavao City 8000..."
    }

    # Preprocess
    processed = preprocess_applicant_data(raw_data)

    # Print result
    print(json.dumps(processed, indent=2))