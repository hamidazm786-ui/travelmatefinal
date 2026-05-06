# TravelMate AI — Backend

FastAPI backend for the TravelMate AI travel planning assistant.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Uvicorn |
| Primary LLM | Groq (llama3-70b-8192) — Free |
| Fallback LLM | Google Gemini 1.5 Flash |
| Web Search | Tavily Search API |
| File Parsing | pypdf + python-docx |
| Settings | pydantic-settings (.env) |
| Frontend | Vite + React + TypeScript (separate repo) |

---

## Quick Start

### 1. Create & activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys:

```env
GROQ_API_KEY=your_groq_key        # https://console.groq.com
GEMINI_API_KEY=your_gemini_key    # https://aistudio.google.com
TAVILY_API_KEY=your_tavily_key    # https://app.tavily.com
SECRET_KEY=any_random_32_char_string
```

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

Server starts at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## Get Free API Keys

| Service | Link | Free Tier |
|---------|------|-----------|
| Groq | https://console.groq.com | 30 req/min — very generous |
| Google Gemini | https://aistudio.google.com | 15 req/min free |
| Tavily | https://app.tavily.com | 1000 req/month free |

---

## Project Structure

```
travelmate-backend/
├── main.py                         # FastAPI app entry point
├── requirements.txt
├── .env                            # Your secrets (NOT committed)
├── .env.example                    # Template (safe to commit)
│
├── app/
│   ├── core/
│   │   ├── config.py               # Pydantic settings — reads .env
│   │   └── logging.py              # Structured logging
│   │
│   ├── schemas/
│   │   └── travel.py               # All Pydantic request/response models
│   │
│   ├── services/
│   │   ├── llm_groq.py             # Groq API calls (primary LLM)
│   │   ├── llm_gemini.py           # Gemini API calls (fallback LLM)
│   │   ├── llm_router.py           # Auto fallback: Groq → Gemini
│   │   ├── search_tavily.py        # Tavily web search (flights/hotels/activities)
│   │   ├── travel_planner.py       # Core business logic: search → LLM → plan
│   │   ├── chat_service.py         # Conversational AI with session memory
│   │   └── file_analyzer.py        # PDF/DOCX/TXT extraction + AI analysis
│   │
│   └── api/
│       └── v1/
│           ├── router.py           # Mounts all route modules
│           └── routes/
│               ├── health.py       # GET  /api/v1/health/
│               ├── travel.py       # POST /api/v1/travel/plan
│               ├── chat.py         # POST /api/v1/chat/message
│               ├── search.py       # GET  /api/v1/search/*
│               └── files.py        # POST /api/v1/files/analyze
│
├── frontend-integration/
│   └── src/
│       ├── lib/api/
│       │   ├── client.ts           # Axios instance (copy to frontend)
│       │   ├── types.ts            # TypeScript types (copy to frontend)
│       │   └── travelmate.ts       # All API functions (copy to frontend)
│       ├── hooks/
│       │   └── useTravelMate.ts    # React Query hooks (copy to frontend)
│       └── store/
│           └── travelStore.ts      # Zustand store (copy to frontend)
│
└── tests/
    └── test_travel_route.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service info |
| GET | `/api/v1/health/` | Health + API key status |
| POST | `/api/v1/travel/plan` | Generate full travel plan |
| POST | `/api/v1/chat/message` | Chat with AI assistant |
| DELETE | `/api/v1/chat/session/{id}` | Clear chat history |
| POST | `/api/v1/search/all` | Search flights + hotels + activities |
| GET | `/api/v1/search/destination` | Destination overview |
| GET | `/api/v1/search/flights` | Flight search |
| GET | `/api/v1/search/hotels` | Hotel search |
| GET | `/api/v1/search/activities` | Activities search |
| POST | `/api/v1/files/analyze` | Upload & analyze travel doc |

---

## Frontend Integration

Copy these files to your Vite+React frontend:

```
frontend-integration/src/lib/api/client.ts    → src/lib/api/client.ts
frontend-integration/src/lib/api/types.ts     → src/lib/api/types.ts
frontend-integration/src/lib/api/travelmate.ts → src/lib/api/travelmate.ts
frontend-integration/src/hooks/useTravelMate.ts → src/hooks/useTravelMate.ts
frontend-integration/src/store/travelStore.ts  → src/store/travelStore.ts
frontend-integration/.env.local               → .env.local (in your frontend root)
```

Then in any component:

```tsx
import { useTravelPlan, useChat, useFileAnalysis } from "@/hooks/useTravelMate";

// Generate a plan
const { mutate: planTrip, data: plan, isPending } = useTravelPlan();
planTrip({ origin: "Lahore", destination: "Istanbul", ... });

// Chat
const { sendMessage, history, isLoading } = useChat();
sendMessage.mutate({ message: "What's the best time to visit Istanbul?" });

// Upload file
const { mutate: analyzeDoc, data: analysis } = useFileAnalysis();
analyzeDoc(selectedFile);
```

---

## Run Tests

```bash
pytest tests/ -v
```

---

## LLM Fallback Chain

```
User Request
     │
     ▼
Groq llama3-70b ──── success ──► Response
     │ (fail/rate-limit)
     ▼
Groq mixtral ──────── success ──► Response  
     │ (fail)
     ▼
Gemini Flash ────── success ──► Response
     │ (fail)
     ▼
  Error 500
```
