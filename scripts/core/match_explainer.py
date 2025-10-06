"""
Match Explanation Generator
Generates human-readable explanations for why candidates match queries
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MatchExplainer:
    """Generate human-readable match explanations for search results"""

    def explain(
        self,
        candidate: Dict[str, Any],
        parsed_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate match explanation for a candidate

        Args:
            candidate: Result from IntelligentSearchEngine.search()
            parsed_query: Output from GeminiQueryParser.parse()

        Returns:
            Dictionary with candidate info, scores, and match reasons
        """
        payload = candidate['payload']
        filters = parsed_query['filters']

        # Extract candidate info
        result = {
            "candidate": {
                "id": payload.get('id'),
                "name": payload.get('full_name'),
                "email": payload.get('email'),
                "job_title": payload.get('job_title'),
                "experience_years": payload.get('total_years_experience', 0),
                "tenure_years": payload.get('longest_tenure_years', 0),
                "location": payload.get('location'),
                "education": payload.get('education_level'),
                "current_company": payload.get('current_company'),
                "current_stage": payload.get('current_stage'),
                "resume_url": payload.get('resume_url'),
                "date_applied": payload.get('date_applied')
            },
            "scores": {
                "final_score": round(candidate['final_score'], 3),
                "semantic_score": round(candidate['semantic_score'], 3),
                "skills_match_score": round(candidate['skills_match_score'], 2),
                "vector_breakdown": {
                    name: round(score, 3)
                    for name, score in candidate.get('vector_scores', {}).items()
                }
            },
            "match_reasons": [],
            "resume_snippet": self._get_resume_snippet(payload)
        }

        # Generate match reasons
        reasons = []

        # Experience match
        exp = payload.get('total_years_experience', 0)
        if filters.get('min_experience') is not None:
            min_exp = filters['min_experience']
            if exp >= min_exp:
                years_over = exp - min_exp
                reasons.append(f"✓ {exp:.1f} years experience (exceeds {min_exp}+ requirement by {years_over:.1f} years)")
            else:
                reasons.append(f"⚠ {exp:.1f} years experience (below {min_exp}+ requirement)")

        if filters.get('max_experience') is not None:
            max_exp = filters['max_experience']
            if exp <= max_exp:
                reasons.append(f"✓ {exp:.1f} years experience (within 0-{max_exp} range)")
            else:
                reasons.append(f"⚠ {exp:.1f} years experience (above {max_exp} maximum)")

        # Location match
        location = payload.get('location', '')
        if filters.get('location'):
            required_location = filters['location']
            if required_location in location:
                reasons.append(f"✓ Located in {location}")
            else:
                reasons.append(f"⚠ Located in {location} (requested: {required_location})")

        # Education match
        education = payload.get('education_level', '')
        if filters.get('education_level'):
            required_edu = filters['education_level']
            if education == required_edu:
                reasons.append(f"✓ {education} (matches requirement)")
            else:
                reasons.append(f"⚠ {education} (requested: {required_edu})")

        # Skills match
        if filters.get('required_skills'):
            skills_text = payload.get('skills_extracted', '').lower()
            matched_skills = []
            missing_skills = []

            for skill in filters['required_skills']:
                if skill.lower() in skills_text:
                    matched_skills.append(skill)
                else:
                    missing_skills.append(skill)

            if matched_skills:
                reasons.append(f"✓ Has required skills: {', '.join(matched_skills)}")

            if missing_skills:
                reasons.append(f"⚠ Missing skills: {', '.join(missing_skills)}")

        # Seniority match
        if filters.get('seniority_keywords'):
            job_title = payload.get('job_title', '').lower()
            seniority_found = []

            for keyword in filters['seniority_keywords']:
                if keyword.lower() in job_title:
                    seniority_found.append(keyword)

            if seniority_found:
                reasons.append(f"✓ Seniority level: {', '.join(seniority_found)} position")

        # Job title relevance
        job_title = payload.get('job_title', '')
        if job_title:
            reasons.append(f"📋 Current role: {job_title}")

        # Semantic match explanation
        semantic_score = candidate['semantic_score']
        if semantic_score >= 0.7:
            reasons.append(f"🎯 Strong semantic match (score: {semantic_score:.2f})")
        elif semantic_score >= 0.5:
            reasons.append(f"🎯 Good semantic match (score: {semantic_score:.2f})")
        else:
            reasons.append(f"🎯 Moderate semantic match (score: {semantic_score:.2f})")

        result['match_reasons'] = reasons

        return result

    def _get_resume_snippet(self, payload: Dict[str, Any], max_length: int = 200) -> str:
        """Extract relevant snippet from resume"""
        resume_text = payload.get('resume_full_text', '')

        if not resume_text:
            return ""

        # Trim to max length
        if len(resume_text) > max_length:
            return resume_text[:max_length] + "..."

        return resume_text

    def format_result(self, explained_result: Dict[str, Any]) -> str:
        """
        Format explained result as human-readable text

        Args:
            explained_result: Output from explain()

        Returns:
            Formatted string
        """
        candidate = explained_result['candidate']
        scores = explained_result['scores']
        reasons = explained_result['match_reasons']

        lines = []
        lines.append(f"Name: {candidate['name']}")
        lines.append(f"Email: {candidate['email']}")
        lines.append(f"Job Title: {candidate['job_title']}")
        lines.append(f"Experience: {candidate['experience_years']:.1f} years")
        lines.append(f"Location: {candidate['location']}")
        lines.append(f"Education: {candidate['education']}")
        lines.append(f"")
        lines.append(f"Match Score: {scores['final_score']:.3f}")
        lines.append(f"  - Semantic: {scores['semantic_score']:.3f}")
        lines.append(f"  - Skills: {scores['skills_match_score']:.2f}")

        if scores['vector_breakdown']:
            lines.append(f"  - Vector scores:")
            for vector_name, score in scores['vector_breakdown'].items():
                lines.append(f"      {vector_name}: {score:.3f}")

        lines.append(f"")
        lines.append(f"Match Reasons:")
        for reason in reasons:
            lines.append(f"  {reason}")

        if explained_result['resume_snippet']:
            lines.append(f"")
            lines.append(f"Resume Preview:")
            lines.append(f"  {explained_result['resume_snippet']}")

        if candidate['resume_url']:
            lines.append(f"")
            lines.append(f"Full Resume: {candidate['resume_url']}")

        return "\n".join(lines)


# Test the explainer
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from load_env import load_env
    from query_parser import GeminiQueryParser
    from intelligent_search import IntelligentSearchEngine

    load_env()

    logging.basicConfig(level=logging.INFO)

    # Initialize components
    parser = GeminiQueryParser()
    engine = IntelligentSearchEngine()
    explainer = MatchExplainer()

    print("\n" + "=" * 80)
    print("TESTING MATCH EXPLAINER")
    print("=" * 80)

    # Test query
    query = "Senior civil engineer in Manila with AutoCAD, 5+ years"

    print(f"\nQuery: {query}")
    print("─" * 80)

    # Parse
    parsed = parser.parse(query)

    # Search
    results = engine.search(parsed, limit=3)

    # Explain and format
    print(f"\nTop {len(results)} results with explanations:\n")

    for i, result in enumerate(results, 1):
        explained = explainer.explain(result, parsed)
        formatted = explainer.format_result(explained)

        print(f"\n[{i}] " + "═" * 76)
        print(formatted)
        print("═" * 80)

    print("\n✓ Test complete")
