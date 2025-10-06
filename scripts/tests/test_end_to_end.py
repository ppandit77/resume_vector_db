"""
End-to-End Test of Intelligent Search System
Tests the complete pipeline: Query Parsing → Search → Explanation
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.load_env import load_env
from core.query_parser import GeminiQueryParser
from core.intelligent_search import IntelligentSearchEngine
from core.match_explainer import MatchExplainer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_search_pipeline():
    """Test the complete search pipeline"""

    load_env()

    print("\n" + "=" * 80)
    print("END-TO-END INTELLIGENT SEARCH TEST")
    print("=" * 80)

    # Initialize components
    print("\n[SETUP] Initializing components...")
    parser = GeminiQueryParser()
    engine = IntelligentSearchEngine()
    explainer = MatchExplainer()
    print("✓ All components initialized\n")

    # Test queries
    test_queries = [
        {
            "name": "Test 1: Senior Engineer with Skills and Location",
            "query": "Senior civil engineer in Manila with AutoCAD, 5+ years",
            "expected_filters": ["min_experience", "location", "required_skills"]
        },
        {
            "name": "Test 2: Python Developer with Framework",
            "query": "Python developer with Django and React",
            "expected_filters": ["required_skills"]
        },
        {
            "name": "Test 3: Recent Graduate with Experience Filter",
            "query": "Recent graduate with marketing skills in Cebu",
            "expected_filters": ["max_experience", "required_skills", "location"]
        },
        {
            "name": "Test 4: Education Requirement",
            "query": "Project manager with master's degree, 10+ years",
            "expected_filters": ["education_level", "min_experience"]
        },
        {
            "name": "Test 5: Simple Role Search",
            "query": "Software engineer",
            "expected_filters": []
        }
    ]

    results_summary = []

    for test in test_queries:
        print("\n" + "=" * 80)
        print(f"{test['name']}")
        print("=" * 80)
        print(f"Query: \"{test['query']}\"")
        print("─" * 80)

        try:
            # Step 1: Parse query
            print("\n[STEP 1] Parsing query...")
            parsed = parser.parse(test['query'])

            print(f"  Search Intent: '{parsed['search_intent']}'")
            print(f"  Filters Extracted:")
            filters_found = []
            for key, value in parsed['filters'].items():
                if value is not None:
                    print(f"    - {key}: {value}")
                    filters_found.append(key)

            if not filters_found:
                print(f"    (no filters)")

            # Verify expected filters
            for expected in test['expected_filters']:
                if expected in filters_found:
                    print(f"  ✓ Expected filter '{expected}' found")
                else:
                    print(f"  ⚠ Expected filter '{expected}' NOT found")

            # Step 2: Search
            print(f"\n[STEP 2] Searching candidates...")
            search_results = engine.search(parsed, limit=5)

            print(f"  ✓ Found {len(search_results)} candidates")

            if search_results:
                top_score = search_results[0]['final_score']
                lowest_score = search_results[-1]['final_score']
                print(f"  Score range: {top_score:.3f} to {lowest_score:.3f}")

            # Step 3: Explain results
            print(f"\n[STEP 3] Generating explanations...")
            explained_results = []

            for result in search_results:
                explained = explainer.explain(result, parsed)
                explained_results.append(explained)

            print(f"  ✓ Generated {len(explained_results)} explanations")

            # Display top 3 results
            print(f"\n[RESULTS] Top {min(3, len(explained_results))} candidates:\n")

            for i, result in enumerate(explained_results[:3], 1):
                candidate = result['candidate']
                scores = result['scores']

                print(f"  [{i}] {candidate['name']}")
                print(f"      Job: {candidate['job_title']}")
                print(f"      Experience: {candidate['experience_years']:.1f} years")
                print(f"      Location: {candidate['location']}")
                print(f"      Score: {scores['final_score']:.3f} (semantic: {scores['semantic_score']:.3f}, skills: {scores['skills_match_score']:.2f})")

                # Show top 3 match reasons
                print(f"      Reasons:")
                for reason in result['match_reasons'][:3]:
                    print(f"        {reason}")
                print()

            # Summary
            test_result = {
                "name": test['name'],
                "query": test['query'],
                "candidates_found": len(search_results),
                "top_score": search_results[0]['final_score'] if search_results else 0,
                "status": "✓ PASS"
            }

            results_summary.append(test_result)

            print(f"✓ {test['name']} completed successfully")

        except Exception as e:
            logger.error(f"✗ Test failed: {e}", exc_info=True)
            test_result = {
                "name": test['name'],
                "query": test['query'],
                "candidates_found": 0,
                "top_score": 0,
                "status": f"✗ FAIL: {str(e)}"
            }
            results_summary.append(test_result)

    # Final summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for result in results_summary:
        print(f"\n{result['status']} {result['name']}")
        print(f"  Query: {result['query']}")
        print(f"  Results: {result['candidates_found']} candidates")
        if result['candidates_found'] > 0:
            print(f"  Top Score: {result['top_score']:.3f}")

    # Overall status
    total_tests = len(results_summary)
    passed_tests = sum(1 for r in results_summary if "PASS" in r['status'])

    print("\n" + "=" * 80)
    print(f"OVERALL: {passed_tests}/{total_tests} tests passed")
    print("=" * 80)

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! System is ready for production.")
        return True
    else:
        print(f"\n⚠ {total_tests - passed_tests} test(s) failed. Review errors above.")
        return False


if __name__ == "__main__":
    try:
        success = test_search_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
