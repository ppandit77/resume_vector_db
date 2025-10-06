# Recruiter Dashboard - Streamlit UI

A beautiful, intuitive UI for intelligent candidate search.

## Quick Start

### 1. Install Streamlit (if not already installed)

```bash
pip install streamlit requests pandas
```

Or:

```bash
pip install -r scripts/ui/requirements.txt
```

### 2. Start the FastAPI backend (in one terminal)

```bash
cd /mnt/c/Users/prita/Downloads/SuperLinked
python3 scripts/api/search_api.py
```

API will run on: `http://localhost:8000`

### 3. Start the Streamlit UI (in another terminal)

```bash
cd /mnt/c/Users/prita/Downloads/SuperLinked
streamlit run scripts/ui/recruiter_dashboard.py
```

UI will open at: `http://localhost:8501`

## Features

✅ **Natural Language Search** - Just type what you're looking for
✅ **Auto-Filter Extraction** - Automatically detects experience, location, skills, education
✅ **Match Explanations** - See why each candidate matched
✅ **Score Breakdown** - Semantic + Skills match scores
✅ **Saved Searches** - Save common queries for quick access
✅ **Search History** - Recent searches in sidebar
✅ **CSV Export** - Export all results to CSV
✅ **Candidate Selection** - Select multiple for comparison
✅ **Resume Preview** - Quick preview in expandable section

## Example Queries

Try these in the search box:

- "Senior Python developer in Manila with 5+ years experience"
- "Recent graduate with marketing skills in Cebu"
- "Civil engineer with AutoCAD, master's degree"
- "Project manager with 10+ years experience"
- "Software engineer who knows React and Node.js"

## UI Components

### Main Search
- Large search box with placeholder examples
- Real-time search (click "Search" button)
- Clear button to reset

### Sidebar
- **Search Settings**: Adjust number of results (5-50)
- **Saved Searches**: Quick access to saved queries
- **Search History**: Last 5 searches
- **System Status**: API connection indicator

### Results
- **Parsed Filters**: Visual chips showing extracted filters
- **Candidate Cards**: Rich cards with:
  - Name, email, job title
  - Match score with breakdown
  - Experience and tenure
  - Location and education
  - Match reasons (expandable)
  - Resume preview (expandable)
  - Selection checkbox

### Actions
- **Export to CSV**: Download all results
- **Save Search**: Save current query
- **Select Candidates**: Multi-select for comparison

## Troubleshooting

### "Cannot connect to search API"
Make sure FastAPI is running:
```bash
python3 scripts/api/search_api.py
```

### "Module not found: streamlit"
Install Streamlit:
```bash
pip install streamlit
```

### Port already in use
Change the port:
```bash
streamlit run scripts/ui/recruiter_dashboard.py --server.port 8502
```

## Configuration

The UI connects to FastAPI at `http://localhost:8000` by default.

To change this, edit `recruiter_dashboard.py`:
```python
API_BASE_URL = "http://your-api-url:port"
```

## Next Steps

Want to deploy this? Options:

1. **Streamlit Cloud** (Free)
   - Push to GitHub
   - Deploy at streamlit.io/cloud
   - No credit card required

2. **Docker**
   - Both FastAPI + Streamlit in containers
   - Deploy to any cloud provider

3. **Heroku/Railway**
   - Easy deployment with procfiles
   - Auto-scaling available
