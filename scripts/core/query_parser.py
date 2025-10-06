"""
Gemini-powered Natural Language Query Parser
Extracts structured search intent and metadata filters from recruiter queries
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from google import genai

logger = logging.getLogger(__name__)


class GeminiQueryParser:
    """Parse natural language recruiter queries into structured search parameters"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini query parser

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        self.client = genai.Client(api_key=self.api_key)
        logger.info("✓ Gemini query parser initialized")

    def _parse_relative_date(self, date_string: str) -> Optional[int]:
        """
        Convert relative date string to Unix timestamp

        Args:
            date_string: String like "last 30 days", "recent", "after January 2025"

        Returns:
            Unix timestamp (integer) or None
        """
        if not date_string or date_string == "null":
            return None

        date_lower = date_string.lower()
        now = datetime.now()

        # Handle "recent" (last 30 days)
        if "recent" in date_lower:
            return int((now - timedelta(days=30)).timestamp())

        # Handle "last X days/weeks/months"
        if "last" in date_lower:
            if "day" in date_lower:
                # Extract number
                try:
                    days = int(''.join(filter(str.isdigit, date_lower)))
                    return int((now - timedelta(days=days)).timestamp())
                except:
                    pass
            elif "week" in date_lower:
                try:
                    weeks = int(''.join(filter(str.isdigit, date_lower)))
                    return int((now - timedelta(weeks=weeks)).timestamp())
                except:
                    pass
            elif "month" in date_lower:
                try:
                    months = int(''.join(filter(str.isdigit, date_lower)))
                    return int((now - timedelta(days=months*30)).timestamp())
                except:
                    pass

        # Handle specific dates like "after January 2025", "since 2025-01-01"
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(date_string)
            return int(dt.timestamp())
        except:
            pass

        # Try common date formats
        for fmt in ["%B %Y", "%b %Y", "%Y-%m-%d", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_string, fmt)
                return int(dt.timestamp())
            except:
                continue

        return None

    def parse(self, natural_query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured search parameters

        Args:
            natural_query: Natural language query from recruiter
            Example: "Senior civil engineers in Manila with AutoCAD, 5+ years experience"

        Returns:
            Dictionary with:
            - search_intent: What to search for in embeddings
            - filters: Structured metadata filters

        Example output:
        {
            "search_intent": "civil engineer with AutoCAD experience",
            "filters": {
                "min_experience": 5.0,
                "location": "Manila, Philippines",
                "required_skills": ["AutoCAD"],
                "seniority_keywords": ["senior"]
            }
        }
        """
        logger.info(f"\n📝 Parsing query: '{natural_query}'")

        # Build prompt for Gemini
        prompt = f"""You are a recruiter search query parser. Extract structured search parameters from this query:

"{natural_query}"

Extract the following:
1. search_intent: The main role, skills, or qualifications to search for (used for semantic vector search)
2. min_experience: Minimum years of experience (float or null)
3. max_experience: Maximum years of experience (float or null)
4. location: Preferred city/location in Philippines (exact match: "Manila, Philippines", "Quezon City, Philippines", "Cebu City, Philippines", "Davao City, Philippines", etc.) (string or null)
5. education_level: Required education (exact match: "Bachelor's Degree", "Master's Degree", "Doctorate", "Associate's Degree", "Diploma/Vocational", "Not Specified") (string or null)
6. required_skills: Must-have technical skills as a list (e.g., ["AutoCAD", "Python", "Excel"]) (list or null)
7. seniority_keywords: Seniority level indicators like "senior", "junior", "lead", etc. (list or null)
8. desired_job_titles: List of job title keywords to match (e.g., ["Software Engineer", "Developer", "Python Developer"]) (list or null)
9. target_companies: List of company names to search for, including variations (e.g., ["Google", "Microsoft", "Amazon"]) (list or null)
10. application_date: Relative date string for filtering recent applicants (e.g., "last 30 days", "recent", "after January 2025") (string or null)

Important rules:
- For locations, always add ", Philippines" suffix if not present
- For experience, extract numbers like "5+", "3-5", "at least 7", etc.
- Keep search_intent concise and focused on the semantic meaning
- For job titles, extract the specific roles mentioned (e.g., "Software Engineer", "Developer", "Civil Engineer")
- For companies, extract company names mentioned with keywords like "at", "from", "worked at"
- For dates, extract relative time references like "recent", "last 30 days", "after January 2025", "this month"
- Only extract what's explicitly mentioned or strongly implied
- If nothing is mentioned for a field, use null

Return ONLY a valid JSON object with this exact structure:
{{
    "search_intent": "string describing what to search for",
    "filters": {{
        "min_experience": float or null,
        "max_experience": float or null,
        "location": "string or null",
        "education_level": "string or null",
        "required_skills": ["list", "of", "skills"] or null,
        "seniority_keywords": ["list", "of", "levels"] or null,
        "desired_job_titles": ["list", "of", "job", "titles"] or null,
        "target_companies": ["list", "of", "companies"] or null,
        "application_date": "string or null"
    }}
}}

Examples:

Query: "Senior Python developer with Django, 5+ years"
{{
    "search_intent": "Python developer with Django experience",
    "filters": {{
        "min_experience": 5.0,
        "max_experience": null,
        "location": null,
        "education_level": null,
        "required_skills": ["Python", "Django"],
        "seniority_keywords": ["senior"],
        "desired_job_titles": ["Python Developer", "Software Developer"],
        "target_companies": null,
        "application_date": null
    }}
}}

Query: "Software engineer from Google or Microsoft who applied last month"
{{
    "search_intent": "software engineer with experience at top tech companies",
    "filters": {{
        "min_experience": null,
        "max_experience": null,
        "location": null,
        "education_level": null,
        "required_skills": null,
        "seniority_keywords": null,
        "desired_job_titles": ["Software Engineer"],
        "target_companies": ["Google", "Microsoft"],
        "application_date": "last 30 days"
    }}
}}

Query: "Civil engineer in Cebu with AutoCAD"
{{
    "search_intent": "civil engineer with AutoCAD experience",
    "filters": {{
        "min_experience": null,
        "max_experience": null,
        "location": "Cebu City, Philippines",
        "education_level": null,
        "required_skills": ["AutoCAD"],
        "seniority_keywords": null,
        "desired_job_titles": ["Civil Engineer"],
        "target_companies": null,
        "application_date": null
    }}
}}

Query: "Recent marketing manager applicants"
{{
    "search_intent": "marketing manager with recent application",
    "filters": {{
        "min_experience": null,
        "max_experience": null,
        "location": null,
        "education_level": null,
        "required_skills": ["marketing"],
        "seniority_keywords": null,
        "desired_job_titles": ["Marketing Manager"],
        "target_companies": null,
        "application_date": "recent"
    }}
}}

Now parse this query:
"{natural_query}"

Return ONLY the JSON, no other text."""

        try:
            # Call Gemini
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-001',
                contents=prompt,
                config={
                    'temperature': 0.0,
                    'response_modalities': ['TEXT']
                }
            )

            # Extract response text
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            # Parse JSON
            parsed = json.loads(response_text)

            # Validate structure
            if 'search_intent' not in parsed or 'filters' not in parsed:
                raise ValueError("Missing required fields in parsed query")

            logger.info("✓ Query parsed successfully")
            logger.info(f"  Search intent: '{parsed['search_intent']}'")

            filters = parsed['filters']
            if filters.get('min_experience'):
                logger.info(f"  Min experience: {filters['min_experience']} years")
            if filters.get('max_experience'):
                logger.info(f"  Max experience: {filters['max_experience']} years")
            if filters.get('location'):
                logger.info(f"  Location: {filters['location']}")
            if filters.get('education_level'):
                logger.info(f"  Education: {filters['education_level']}")
            if filters.get('required_skills'):
                logger.info(f"  Required skills: {', '.join(filters['required_skills'])}")
            if filters.get('seniority_keywords'):
                logger.info(f"  Seniority: {', '.join(filters['seniority_keywords'])}")
            if filters.get('desired_job_titles'):
                logger.info(f"  Job titles: {', '.join(filters['desired_job_titles'])}")
            if filters.get('target_companies'):
                logger.info(f"  Companies: {', '.join(filters['target_companies'])}")
            if filters.get('application_date'):
                # Convert relative date to Unix timestamp
                date_str = filters['application_date']
                timestamp = self._parse_relative_date(date_str)
                if timestamp:
                    filters['min_date_applied'] = timestamp
                    date_readable = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    logger.info(f"  Applied after: {date_readable} ({date_str})")
                # Remove the string version
                filters.pop('application_date', None)

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response was: {response_text}")

            # Fallback: return query as-is with no filters
            return {
                "search_intent": natural_query,
                "filters": {
                    "min_experience": None,
                    "max_experience": None,
                    "location": None,
                    "education_level": None,
                    "required_skills": None,
                    "seniority_keywords": None,
                    "desired_job_titles": None,
                    "target_companies": None,
                    "min_date_applied": None
                }
            }

        except Exception as e:
            logger.error(f"Error parsing query with Gemini: {e}")

            # Fallback
            return {
                "search_intent": natural_query,
                "filters": {
                    "min_experience": None,
                    "max_experience": None,
                    "location": None,
                    "education_level": None,
                    "required_skills": None,
                    "seniority_keywords": None,
                    "desired_job_titles": None,
                    "target_companies": None,
                    "min_date_applied": None
                }
            }


# Test the parser
if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(__file__))
    from load_env import load_env

    load_env()

    logging.basicConfig(level=logging.INFO)

    parser = GeminiQueryParser()

    # Test queries
    test_queries = [
        "Senior civil engineer in Manila with AutoCAD, 5+ years experience",
        "Python developer with Django and React",
        "Recent graduate with marketing skills in Cebu",
        "Project manager with 10+ years, master's degree",
        "Find me experienced software engineers who know Java and Spring Boot"
    ]

    print("\n" + "=" * 80)
    print("TESTING GEMINI QUERY PARSER")
    print("=" * 80)

    for query in test_queries:
        print(f"\n{'─' * 80}")
        result = parser.parse(query)
        print(f"\nParsed result:")
        print(json.dumps(result, indent=2))

    print("\n" + "=" * 80)
    print("✓ All tests complete")
    print("=" * 80)
