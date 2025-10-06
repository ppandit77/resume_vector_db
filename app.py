"""
Applicant Search - Streamlit UI
Semantic search interface for the applicant database with natural language support
"""
import streamlit as st
import sys
import os
import time

# Add scripts directory to path
sys.path.append('scripts')
from core.simple_qdrant_search import SimpleQdrantSearch

# Page config
st.set_page_config(
    page_title="Applicant Search",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 Applicant Search System")
st.markdown("Semantic search powered by **Gemini Embeddings** + **Qdrant Cloud**")

# Initialize search system (cached)
@st.cache_resource
def init_search():
    """Initialize search system (runs once)"""
    with st.spinner("Initializing search system..."):
        search = SimpleQdrantSearch('data/processed/applicants_with_embeddings_clean.json')
    return search

# Load search system
try:
    search = init_search()
    st.success("✅ Search system ready!")
except Exception as e:
    st.error(f"❌ Failed to initialize search system: {e}")
    st.stop()

# Sidebar for settings
st.sidebar.header("⚙️ Search Settings")

# Number of results
limit = st.sidebar.slider("Number of Results", 1, 50, 10)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 System Info")
st.sidebar.info(f"""
**Storage:** Qdrant Cloud (Europe)
**Records:** 4,889 applicants
**Embedding:** Gemini 3072-dim
**Search:** 3 embeddings (resume + skills + tasks)
""")

# Main search interface
st.markdown("---")

# Search input
st.subheader("🔎 Natural Language Search")

# Query input
query = st.text_input(
    "Search Query",
    placeholder="Example: Civil Engineer with AutoCAD experience"
)

# Filters in expandable section
with st.expander("🔧 Advanced Filters", expanded=False):
    col1, col2, col3 = st.columns(3)

    with col1:
        min_experience = st.number_input(
            "Min Experience (years)",
            min_value=0.0,
            max_value=30.0,
            value=0.0,
            step=0.5
        )

        max_experience = st.number_input(
            "Max Experience (years)",
            min_value=0.0,
            max_value=30.0,
            value=0.0,
            step=0.5,
            help="Leave at 0 for no max limit"
        )

    with col2:
        location = st.selectbox(
            "Location",
            ["Any", "Manila, Philippines", "Quezon City, Philippines", "Cebu City, Philippines", "Davao City, Philippines"]
        )

        education_level = st.selectbox(
            "Education Level",
            ["Any", "Bachelor's Degree", "Master's Degree", "Doctorate", "Associate's Degree", "Diploma/Vocational"]
        )

    with col3:
        st.markdown("**Required Skills**")
        skills_input = st.text_area(
            "Enter skills (one per line)",
            height=100,
            placeholder="AutoCAD\nPython\nProject Management"
        )

# Search button
if st.button("🔍 Search", type="primary", use_container_width=True):
    if not query:
        st.warning("⚠️ Please enter a search query")
    else:
        # Perform search
        with st.spinner("Searching..."):
            start_time = time.time()

            try:
                # Parse skills
                skills_keywords = None
                if skills_input.strip():
                    skills_keywords = [s.strip() for s in skills_input.split('\n') if s.strip()]

                # Simple search with filters
                results = search.search(
                    query=query,
                    min_experience=min_experience if min_experience > 0 else None,
                    max_experience=max_experience if max_experience > 0 else None,
                    location=location if location != "Any" else None,
                    education_level=education_level if education_level != "Any" else None,
                    skills_keywords=skills_keywords,
                    limit=limit
                )

                search_time = time.time() - start_time

                # Display results
                st.success(f"✅ Found {len(results)} results in {search_time:.2f}s")

                if len(results) == 0:
                    st.info("No results found. Try adjusting your query or filters.")
                else:
                    st.markdown("---")
                    st.subheader("📋 Results")

                    # Display each result
                    for i, result in enumerate(results, 1):
                        with st.expander(f"**{i}. {result.get('full_name', 'N/A')}** - {result.get('job_title', 'N/A')}", expanded=(i <= 3)):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Experience", f"{result.get('total_years_experience', 0):.1f} years")

                            with col2:
                                st.metric("Longest Tenure", f"{result.get('longest_tenure', 0):.1f} years")

                            with col3:
                                st.metric("Education", result.get('highest_education_level', 'N/A'))

                            # Skills
                            skills = result.get('skills_list', [])
                            if skills:
                                st.markdown("**🛠️ Skills:**")
                                skills_str = ", ".join(skills[:20])  # Show first 20 skills
                                if len(skills) > 20:
                                    skills_str += f" ... and {len(skills) - 20} more"
                                st.markdown(f"_{skills_str}_")

                            # Resume summary
                            if result.get('resume_summary'):
                                st.markdown("**📄 Resume Summary:**")
                                summary = result.get('resume_summary', '')[:500]
                                if len(result.get('resume_summary', '')) > 500:
                                    summary += "..."
                                st.markdown(f"> {summary}")

            except Exception as e:
                st.error(f"❌ Search failed: {e}")
                st.exception(e)

# Example queries
st.markdown("---")
with st.expander("💡 Example Queries"):
    st.markdown("""
    ### Semantic Search Examples:
    - `Civil Engineer with AutoCAD`
    - `Senior Software Engineer Python`
    - `Data Analyst with SQL experience`
    - `Project Manager construction`

    ### Natural Language Examples:
    - `Find senior civil engineers with at least 5 years of experience`
    - `Search for software developers who know Python and have worked on machine learning`
    - `Show me project managers with construction experience`
    - `Find data analysts with SQL skills and at least 3 years experience`
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>Powered by Superlinked + Gemini + Qdrant | Built with Streamlit</small>
    </div>
    """,
    unsafe_allow_html=True
)
