"""
Streamlit Recruiter Dashboard
Intelligent candidate search UI for recruiters
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="Intelligent Candidate Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .candidate-card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        background-color: white;
    }
    .score-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.875rem;
    }
    .score-high {
        background-color: #d4edda;
        color: #155724;
    }
    .score-medium {
        background-color: #fff3cd;
        color: #856404;
    }
    .score-low {
        background-color: #f8d7da;
        color: #721c24;
    }
    .match-reason {
        padding: 0.5rem;
        margin: 0.25rem 0;
        background-color: #f8f9fa;
        border-left: 3px solid #007bff;
        border-radius: 0.25rem;
    }
    .filter-chip {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        background-color: #e3f2fd;
        color: #1976d2;
        border-radius: 1rem;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Session state initialization
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'saved_searches' not in st.session_state:
    st.session_state.saved_searches = []
if 'selected_candidates' not in st.session_state:
    st.session_state.selected_candidates = []
if 'last_results' not in st.session_state:
    st.session_state.last_results = None


def call_search_api(query: str, limit: int = 20) -> dict:
    """Call the FastAPI search endpoint"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={"query": query, "limit": limit, "enable_reranking": True},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to search API. Make sure FastAPI is running on port 8000.")
        st.code("python3 scripts/api/search_api.py", language="bash")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Search request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


def get_score_class(score: float) -> str:
    """Get CSS class for score badge"""
    if score >= 0.7:
        return "score-high"
    elif score >= 0.5:
        return "score-medium"
    else:
        return "score-low"


def format_filter_chips(filters: dict) -> str:
    """Format parsed filters as HTML chips"""
    chips = []

    if filters.get('min_experience'):
        chips.append(f'<span class="filter-chip">Experience: {filters["min_experience"]}+ years</span>')

    if filters.get('max_experience'):
        chips.append(f'<span class="filter-chip">Max Experience: {filters["max_experience"]} years</span>')

    if filters.get('location'):
        chips.append(f'<span class="filter-chip">📍 {filters["location"]}</span>')

    if filters.get('education_level'):
        chips.append(f'<span class="filter-chip">🎓 {filters["education_level"]}</span>')

    if filters.get('required_skills'):
        skills_str = ", ".join(filters['required_skills'])
        chips.append(f'<span class="filter-chip">💡 {skills_str}</span>')

    if filters.get('seniority_keywords'):
        seniority_str = ", ".join(filters['seniority_keywords'])
        chips.append(f'<span class="filter-chip">⭐ {seniority_str}</span>')

    if filters.get('desired_job_titles'):
        titles_str = ", ".join(filters['desired_job_titles'])
        chips.append(f'<span class="filter-chip">💼 {titles_str}</span>')

    if filters.get('target_companies'):
        companies_str = ", ".join(filters['target_companies'])
        chips.append(f'<span class="filter-chip">🏢 {companies_str}</span>')

    if filters.get('min_date_applied'):
        date_ts = filters['min_date_applied']
        date_str = datetime.fromtimestamp(date_ts).strftime('%b %d, %Y')
        chips.append(f'<span class="filter-chip">📅 Applied after {date_str}</span>')

    return "".join(chips) if chips else '<span class="filter-chip">No filters applied</span>'


def display_candidate_card(result: dict, index: int):
    """Display a candidate card with all details"""
    candidate = result['candidate']
    scores = result['scores']
    reasons = result['match_reasons']

    # Container for the card
    with st.container():
        # Header row
        col1, col2, col3, col4 = st.columns([4, 2, 1, 1])

        with col1:
            st.markdown(f"### {candidate['name']}")
            st.markdown(f"**{candidate['job_title']}**")
            st.caption(f"📧 {candidate['email']}")

        with col2:
            st.metric(
                "Match Score",
                f"{scores['final_score']:.3f}",
                f"Semantic: {scores['semantic_score']:.3f}"
            )

        with col3:
            st.metric(
                "Experience",
                f"{candidate['experience_years']:.1f} yrs",
                f"Tenure: {candidate['tenure_years']:.1f}"
            )

        with col4:
            # Selection checkbox
            is_selected = candidate['id'] in st.session_state.selected_candidates
            if st.checkbox(
                "Select",
                value=is_selected,
                key=f"select_{candidate['id']}_{index}"
            ):
                if candidate['id'] not in st.session_state.selected_candidates:
                    st.session_state.selected_candidates.append(candidate['id'])
            else:
                if candidate['id'] in st.session_state.selected_candidates:
                    st.session_state.selected_candidates.remove(candidate['id'])

        # Details row
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**Location:** {candidate['location']}")
            st.markdown(f"**Education:** {candidate['education']}")

        with col2:
            st.markdown(f"**Company:** {candidate.get('current_company', 'N/A')}")
            st.markdown(f"**Stage:** {candidate.get('current_stage', 'N/A')}")

            # Format date_applied
            date_applied = candidate.get('date_applied')
            if date_applied:
                date_str = datetime.fromtimestamp(date_applied).strftime('%b %d, %Y')
                st.markdown(f"**Applied:** {date_str}")
            else:
                st.markdown(f"**Applied:** N/A")

        with col3:
            st.markdown("**Score Breakdown:**")
            st.markdown(f"- Semantic: {scores['semantic_score']:.3f}")
            st.markdown(f"- Skills Match: {scores['skills_match_score']:.2f}")

        # Match reasons
        with st.expander("📋 Match Reasons", expanded=False):
            for reason in reasons:
                st.markdown(f"- {reason}")

        # Resume snippet
        if result.get('resume_snippet'):
            with st.expander("📄 Resume Preview"):
                st.text(result['resume_snippet'])
                if candidate.get('resume_url'):
                    st.markdown(f"[View Full Resume]({candidate['resume_url']})")

        st.divider()


# Sidebar
with st.sidebar:
    st.title("🔍 Search Settings")

    # Search limit
    result_limit = st.slider(
        "Number of results",
        min_value=5,
        max_value=50,
        value=20,
        step=5
    )

    st.divider()

    # Saved Searches
    st.subheader("💾 Saved Searches")

    if st.session_state.saved_searches:
        for i, saved in enumerate(st.session_state.saved_searches):
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(
                    saved['query'],
                    key=f"saved_{i}",
                    use_container_width=True
                ):
                    st.session_state.current_query = saved['query']
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{i}"):
                    st.session_state.saved_searches.pop(i)
                    st.rerun()
    else:
        st.caption("No saved searches yet")

    st.divider()

    # Search History
    st.subheader("📜 Recent Searches")

    if st.session_state.search_history:
        for i, query in enumerate(reversed(st.session_state.search_history[-5:])):
            if st.button(query, key=f"history_{i}", use_container_width=True):
                st.session_state.current_query = query
                st.rerun()
    else:
        st.caption("No search history")

    st.divider()

    # System Status
    st.subheader("⚙️ System Status")
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            st.success("✓ API Connected")
        else:
            st.error("✗ API Error")
    except:
        st.error("✗ API Offline")


# Main content
st.title("🎯 Intelligent Candidate Search")
st.markdown("Search for candidates using natural language. Ask for specific skills, experience, location, or education.")

# Example queries
with st.expander("💡 Example Queries"):
    st.markdown("""
    - "Senior Python developer in Manila with 5+ years experience"
    - "Recent graduate with marketing skills in Cebu"
    - "Civil engineer with AutoCAD, master's degree"
    - "Project manager with 10+ years experience"
    - "Software engineer who knows React and Node.js"
    """)

# Search input
query = st.text_input(
    "Search Query",
    value=st.session_state.get('current_query', ''),
    placeholder="e.g., Senior Python developer in Manila, 5+ years",
    label_visibility="collapsed",
    key="search_input"
)

# Action buttons
col1, col2, col3, col4 = st.columns([2, 2, 2, 6])

with col1:
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

with col2:
    if query and st.button("💾 Save Search", use_container_width=True):
        if query not in [s['query'] for s in st.session_state.saved_searches]:
            st.session_state.saved_searches.append({
                'query': query,
                'saved_at': datetime.now().isoformat()
            })
            st.success("Search saved!")
            st.rerun()

with col3:
    if st.button("🔄 Clear", use_container_width=True):
        st.session_state.current_query = ''
        st.session_state.last_results = None
        st.session_state.selected_candidates = []
        st.rerun()

# Perform search
if search_clicked and query:
    with st.spinner("🔍 Searching candidates..."):
        # Add to history
        if query not in st.session_state.search_history:
            st.session_state.search_history.append(query)

        # Call API
        results = call_search_api(query, result_limit)

        if results:
            st.session_state.last_results = results

# Display results
if st.session_state.last_results:
    results = st.session_state.last_results

    st.success(f"✓ Found {results['total_results']} candidates")

    # Parsed filters
    st.markdown("### 📊 Parsed Filters")
    st.markdown(format_filter_chips(results['parsed_filters']), unsafe_allow_html=True)

    st.divider()

    # Export and comparison buttons
    col1, col2, col3 = st.columns([2, 2, 8])

    with col1:
        if st.button("📥 Export All to CSV", use_container_width=True):
            # Prepare DataFrame
            candidates_data = []
            for result in results['results']:
                candidate = result['candidate']
                scores = result['scores']
                # Format date_applied for CSV
                date_applied = candidate.get('date_applied')
                date_str = datetime.fromtimestamp(date_applied).strftime('%Y-%m-%d') if date_applied else 'N/A'

                candidates_data.append({
                    'Name': candidate['name'],
                    'Email': candidate['email'],
                    'Job Title': candidate['job_title'],
                    'Experience (years)': candidate['experience_years'],
                    'Location': candidate['location'],
                    'Education': candidate['education'],
                    'Date Applied': date_str,
                    'Match Score': scores['final_score'],
                    'Semantic Score': scores['semantic_score'],
                    'Skills Match': scores['skills_match_score'],
                    'Resume URL': candidate.get('resume_url', '')
                })

            df = pd.DataFrame(candidates_data)
            csv = df.to_csv(index=False)

            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col2:
        if st.session_state.selected_candidates:
            st.info(f"✓ {len(st.session_state.selected_candidates)} selected")

    st.divider()

    # Results
    st.markdown(f"### 📋 Results ({results['total_results']} candidates)")

    # Display each candidate
    for i, result in enumerate(results['results']):
        display_candidate_card(result, i)

# Footer
st.divider()
st.caption("🤖 Powered by Intelligent Search Engine | Gemini Embeddings + Qdrant Vector DB")
