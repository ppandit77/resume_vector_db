# 🎯 Intelligent Candidate Search System

> AI-powered semantic search for recruiting - Find the perfect candidates using natural language queries

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Cloud-purple.svg)](https://qdrant.tech/)
[![Gemini](https://img.shields.io/badge/Google-Gemini-orange.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 What This Does

Transform your recruiting workflow with AI-powered semantic search. Simply ask for candidates in plain English:

```
"Senior Python developer in Manila with 5+ years experience"
"Recent marketing graduates who applied last month"
"Civil engineer with AutoCAD from top companies"
```

The system understands context, extracts filters, and returns perfectly matched candidates with explanations.

---

## ✨ Key Features

### 🧠 **Intelligent Query Parsing**
- Natural language understanding with Gemini AI
- Automatic filter extraction (skills, location, experience, education, job titles, companies, dates)
- Dual-API fallback system (Gemini → OpenAI) for 99.9% uptime

### 🔍 **Advanced Vector Search**
- Multi-vector architecture (resume, skills, tasks)
- Weighted fusion search (50% resume + 30% skills + 20% tasks)
- Gemini embeddings (3072 dimensions) for semantic understanding
- Skills-based re-ranking (70% semantic + 30% skills match)

### 📊 **Rich Filtering**
- Experience range (min/max years)
- Location matching (fuzzy)
- Education level
- Job titles (full-text search with variations)
- Current/past companies (flexible matching)
- Application date (relative dates like "last 30 days")
- Required skills
- Seniority levels

### 🎨 **Beautiful UI**
- Clean Streamlit dashboard for recruiters
- Real-time search with match explanations
- CSV export functionality
- Search history and saved searches
- Interactive candidate cards

### 🔌 **Production-Ready API**
- FastAPI REST endpoint with auto-documentation
- Pydantic validation
- Comprehensive error handling
- Health checks and monitoring
- OpenAPI/Swagger UI at `/docs`

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Natural Query  │ "Senior Python dev in Manila, 5+ years"
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Query Parser (Gemini AI + OpenAI Fallback)    │
│  ✓ Extract filters                              │
│  ✓ Generate embedding text                      │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Intelligent Search Engine                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Resume    │  │   Skills    │  │  Tasks  │ │
│  │  Vector 50% │  │  Vector 30% │  │Vector 20%│ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│  Multi-vector weighted fusion + pre-filtering   │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Skills Re-Ranker                               │
│  70% semantic score + 30% skills match          │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Match Explainer                                │
│  ✓ Generate human-readable reasons              │
│  ✓ Score breakdown                              │
│  ✓ Resume snippets                              │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Results + API  │
└─────────────────┘
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Embeddings** | Google Gemini (3072-dim) | Semantic understanding |
| **Vector DB** | Qdrant Cloud | Fast similarity search |
| **Query Parser** | Gemini AI + OpenAI | Natural language processing |
| **API** | FastAPI + Pydantic | REST endpoints |
| **UI** | Streamlit | Recruiter dashboard |
| **Language** | Python 3.12+ | Core logic |

---

## 📦 Installation

### Prerequisites
- Python 3.12+
- Qdrant Cloud account (free tier: https://cloud.qdrant.io/)
- Google Gemini API key (free: https://makersuite.google.com/app/apikey)
- OpenAI API key (optional, for fallback: https://platform.openai.com/api-keys)

### 1. Clone Repository
```bash
git clone https://github.com/ppandit77/resume_vector_db.git
cd resume_vector_db
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create `.env` file in project root:
```bash
# Required: Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Required: Qdrant Cloud
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION=applicants_production

# Optional: OpenAI Fallback
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

### 5. Create Qdrant Indexes
```bash
python3 scripts/migrations/create_payload_indexes.py
```

---

## 🚀 Usage

### Start the FastAPI Server
```bash
python3 scripts/api/search_api.py
```
API runs at: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Start the Streamlit UI
```bash
streamlit run scripts/ui/recruiter_dashboard.py
```
Dashboard runs at: http://localhost:8501

### API Example
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Senior Python developer with Django, 5+ years in Manila",
    "limit": 10,
    "enable_reranking": true
  }'
```

**Response:**
```json
{
  "query": "Senior Python developer with Django, 5+ years in Manila",
  "parsed_filters": {
    "min_experience": 5.0,
    "location": "Manila, Philippines",
    "required_skills": ["Python", "Django"],
    "seniority_keywords": ["senior"]
  },
  "total_results": 10,
  "results": [
    {
      "candidate": {
        "name": "John Doe",
        "email": "john@example.com",
        "job_title": "Senior Software Engineer",
        "experience_years": 7.5,
        "location": "Manila, Philippines",
        "education": "Bachelor's Degree"
      },
      "scores": {
        "final_score": 0.856,
        "semantic_score": 0.782,
        "skills_match_score": 1.0
      },
      "match_reasons": [
        "✓ 7.5 years experience (exceeds 5+ requirement by 2.5 years)",
        "✓ Located in Manila, Philippines",
        "✓ Has required skills: Python, Django",
        "✓ Seniority level: Senior position",
        "🎯 Strong semantic match (score: 0.78)"
      ]
    }
  ],
  "api_used": "gemini",
  "fallback_used": false,
  "warning": null
}
```

---

## 📖 API Documentation

### `POST /search`
Search for candidates using natural language.

**Request:**
```json
{
  "query": "string",          // Natural language query
  "limit": 20,                // Max results (1-100)
  "enable_reranking": true    // Skills-based re-ranking
}
```

**Response Fields:**
- `query`: Original search query
- `parsed_filters`: Extracted filters (experience, location, skills, etc.)
- `total_results`: Number of candidates found
- `results`: Array of candidate objects with scores and match reasons
- `api_used`: Which AI parsed the query ("gemini", "openai", or "none")
- `fallback_used`: Boolean indicating if fallback was triggered
- `warning`: Optional warning message

### `GET /health`
System health check with component status.

### `GET /stats`
Collection statistics (total candidates, vector info, models used).

---

## 🔧 Configuration

### Embedding Model
Default: `gemini-embedding-001` (3072 dimensions)

Change in `.env`:
```bash
GEMINI_MODEL=models/gemini-embedding-001
```

### Query Parser Models
- **Primary:** `gemini-2.0-flash-001`
- **Fallback:** `gpt-4o-mini`

### Vector Weights
Customize in `scripts/core/intelligent_search.py`:
```python
vector_weights = {
    "resume": 0.5,   # 50% weight on resume content
    "skills": 0.3,   # 30% weight on skills
    "tasks": 0.2     # 20% weight on job tasks
}
```

### Re-ranking Weights
Customize in `scripts/core/intelligent_search.py`:
```python
final_score = (0.7 * semantic_score) + (0.3 * skills_match_score)
```

---

## 📁 Project Structure

```
resume_vector_db/
├── scripts/
│   ├── core/
│   │   ├── query_parser.py           # Gemini + OpenAI query parsing
│   │   ├── intelligent_search.py     # Multi-vector search engine
│   │   ├── match_explainer.py        # Match reason generation
│   │   └── load_env.py               # Environment loader
│   ├── api/
│   │   └── search_api.py             # FastAPI REST endpoint
│   ├── ui/
│   │   └── recruiter_dashboard.py    # Streamlit UI
│   └── migrations/
│       └── create_payload_indexes.py # Qdrant index setup
├── docs/
│   └── CONTEXT.md                    # Development history
├── .env                              # API keys (gitignored)
├── .gitignore                        # Git exclusions
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

---

## 🌟 Example Queries

```
✅ "Senior civil engineer in Manila with AutoCAD, 5+ years"
✅ "Recent graduate with marketing skills in Cebu"
✅ "Python developer who knows React and Node.js"
✅ "Project manager with 10+ years, master's degree"
✅ "Software engineer from Google who applied last month"
✅ "Mortgage underwriters in last 45 days"
✅ "Marketing manager at Unilever or P&G"
```

---

## 🔒 Security

- **API keys protected:** `.env` file is gitignored
- **No credentials in code:** All secrets in environment variables
- **Input validation:** Pydantic models validate all API inputs
- **Rate limiting:** Recommended for production deployment

---

## 🚢 Deployment

### Option 1: Render (Free Tier)
1. Connect GitHub repo to Render
2. Add environment variables in Render dashboard
3. Deploy FastAPI as Web Service
4. Deploy Streamlit as separate Web Service

### Option 2: Digital Ocean App Platform
1. Create new app from GitHub
2. Configure environment variables
3. Set build command: `pip install -r requirements.txt`
4. Set run command: `python3 scripts/api/search_api.py`

### Option 3: Cloudron
1. Deploy Python app via Cloudron
2. Configure .env variables
3. Map ports 8000 (API) and 8501 (UI)

---

## 🎯 Performance

- **Search latency:** < 500ms (typical)
- **Embedding generation:** ~100ms per query
- **Vector search:** ~50ms (4,889 candidates)
- **Collection size:** 4,889 applicants
- **Vectors per candidate:** 3 (resume, skills, tasks)

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 License

MIT License - see LICENSE file for details

---

## 👤 Author

**Prithvi Pandit** - NightOwl Consulting LLC
- GitHub: [@ppandit77](https://github.com/ppandit77)
- Email: ppandit@nightowl.consulting

---

## 🙏 Acknowledgments

- **Google Gemini** for powerful embeddings and query parsing
- **Qdrant** for fast vector similarity search
- **OpenAI** for reliable fallback parsing
- **FastAPI** for excellent API framework
- **Streamlit** for rapid UI development

---

## 🐛 Known Issues & Roadmap

### Coming Soon:
- [ ] Query caching (LRU cache for repeated searches)
- [ ] API timeouts and retry logic
- [ ] Usage tracking and analytics
- [ ] Prometheus metrics endpoint
- [ ] Batch candidate import via API
- [ ] Advanced search filters (salary range, remote work)
- [ ] Email alerts for new matching candidates
- [ ] Integration with ATS systems

### Known Limitations:
- Requires internet connection for Gemini/OpenAI APIs
- Free tier Qdrant limited to 1GB storage
- UI is single-user (no authentication yet)

---

<div align="center">

**Built with ❤️ using Claude Code**

⭐ Star this repo if you find it useful!

</div>
