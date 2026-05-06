# TravelMate Backend — PostgreSQL Edition

Full-stack AI travel planner with persistent PostgreSQL database.
No PostgreSQL installation needed — uses **Neon** (free cloud Postgres).

---

## What's new in this version

| Feature | Before | Now |
|---|---|---|
| User accounts | ❌ None | ✅ Register / Login / JWT auth |
| Chat history | RAM only (lost on restart) | ✅ PostgreSQL (permanent) |
| Travel plans | RAM only | ✅ PostgreSQL (permanent) |
| User profiles | ❌ None | ✅ Full profile + preferences |
| Dashboard stats | ❌ None | ✅ Total trips, spend, favourites |

---

## Step 1 — Get a FREE PostgreSQL database (Neon)

You do NOT need to install PostgreSQL. Use Neon — free cloud Postgres.

1. Go to **neon.tech** and sign up (free)
2. Click **"New Project"** → name it `travelmate`
3. Click **"Connect"** → select **"Python (asyncpg)"**
4. Copy the connection string — it looks like:
   ```
   postgresql+asyncpg://username:password@ep-xxx.us-east-2.aws.neon.tech/neondb
   ```
5. Paste it into your `.env` file as `DATABASE_URL`

That's it. No installation, no server setup.

---

## Step 2 — Install new dependencies

```bash
# Activate your virtual environment first
venv\Scripts\activate          # Windows
source venv/bin/activate        # Mac/Linux

# Install all packages (including new ones)
pip install -r requirements.txt
```

New packages added:
- `asyncpg` — async PostgreSQL driver (pure Python, no install needed)
- `sqlalchemy` — ORM to work with tables as Python classes
- `alembic` — database migrations
- `python-jose` — JWT token creation and verification
- `passlib[bcrypt]` — secure password hashing

---

## Step 3 — Configure your .env file

Copy `.env` and fill in your values:

```env
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
SECRET_KEY=run: python -c "import secrets; print(secrets.token_hex(32))"
GROQ_API_KEY=gsk_your_key

# Already had these
TAVILY_API_KEY=tvly_your_key
GEMINI_API_KEY=your_key
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 4 — Run the server

```bash
uvicorn main:app --reload --port 8000
```

On first startup you will see:
```
TravelMate starting up...
Database tables ready        ← tables created automatically
TravelMate is ready
```

Open **http://localhost:8000/docs** to see all endpoints.

---

## Project structure

```
travelmate-backend/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # All dependencies
├── .env                             # Your secrets (never commit this)
│
├── app/
│   ├── core/
│   │   ├── config.py               # Settings from .env
│   │   ├── security.py             # JWT + password hashing
│   │   ├── dependencies.py         # get_current_user dependency
│   │   └── logging.py              # Logger setup
│   │
│   ├── db/
│   │   └── database.py             # SQLAlchemy engine + get_db()
│   │
│   ├── models/
│   │   └── models.py               # 4 DB tables as Python classes
│   │
│   ├── schemas/
│   │   ├── auth.py                 # Register/Login request+response
│   │   ├── plans.py                # Travel plan + chat schemas
│   │   └── travel.py               # (existing) travel request schemas
│   │
│   ├── services/
│   │   ├── chat_service.py         # (existing) LLM chat handler
│   │   └── travel_planner.py       # (existing) plan generator
│   │
│   └── api/v1/
│       ├── router.py               # Registers all route groups
│       └── routes/
│           ├── auth.py             # Register, login, profile
│           ├── plans.py            # Travel plan CRUD
│           ├── chat_db.py          # Chat sessions + messages
│           └── travel_db.py        # Generate + auto-save plans
```

---

## Database tables

### users
Stores all registered accounts.
```
id, email, full_name, hashed_password, avatar_url,
preferred_style, preferred_trip_type, home_city,
currency, is_active, total_trips, created_at, last_login_at
```

### travel_plans
Every generated itinerary saved permanently.
```
id, user_id, origin, destination, departure_date, return_date,
duration_days, travelers, budget_usd, budget_level, trip_type,
plan_json (full JSON), summary, total_estimated_cost_usd,
llm_used, status, is_favourite, created_at
```

### chat_sessions
One row per conversation thread.
```
id, user_id, travel_plan_id, title, message_count,
is_active, travel_context_json, created_at, updated_at
```

### chat_messages
Every message in every conversation.
```
id, session_id, role (user/assistant), content,
llm_used, sources (JSON array), created_at
```

---

## All API Endpoints

### Authentication
| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Create account | No |
| POST | `/api/v1/auth/login` | Sign in, get token | No |
| GET | `/api/v1/auth/me` | Get my profile | ✅ Yes |
| PATCH | `/api/v1/auth/me` | Update profile | ✅ Yes |
| POST | `/api/v1/auth/change-password` | Change password | ✅ Yes |
| DELETE | `/api/v1/auth/me` | Delete account | ✅ Yes |

### Travel Planning
| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| POST | `/api/v1/travel/plan` | Generate plan (auto-saves if logged in) | Optional |
| GET | `/api/v1/travel/plan/{id}` | Get a saved plan | ✅ Yes |
| POST | `/api/v1/travel/plan/upload` | Generate from file upload | ✅ Yes |

### Saved Plans
| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| GET | `/api/v1/plans` | List all my plans | ✅ Yes |
| POST | `/api/v1/plans` | Save a plan manually | ✅ Yes |
| GET | `/api/v1/plans/{id}` | Get plan detail | ✅ Yes |
| PATCH | `/api/v1/plans/{id}` | Update status/favourite | ✅ Yes |
| DELETE | `/api/v1/plans/{id}` | Delete plan | ✅ Yes |
| GET | `/api/v1/plans/stats/me` | Dashboard stats | ✅ Yes |

### Chat
| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| POST | `/api/v1/chat/sessions` | Start new chat | ✅ Yes |
| GET | `/api/v1/chat/sessions` | List all chats | ✅ Yes |
| GET | `/api/v1/chat/sessions/{id}` | Get chat + messages | ✅ Yes |
| POST | `/api/v1/chat/sessions/{id}/message` | Send message | ✅ Yes |
| DELETE | `/api/v1/chat/sessions/{id}` | Delete chat | ✅ Yes |

---

## How to use the API (quick test)

### 1. Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Ali Khan","email":"ali@test.com","password":"Test1234"}'
```

### 2. Copy the token from the response, then login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ali@test.com","password":"Test1234"}'
```

### 3. Use token in protected requests
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 4. Generate + auto-save a travel plan
```bash
curl -X POST http://localhost:8000/api/v1/travel/plan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "origin": "Lahore, Pakistan",
    "destination": "Istanbul, Turkey",
    "departure_date": "2025-06-01",
    "return_date": "2025-06-10",
    "duration_days": 9,
    "travelers": 2,
    "budget": "3000",
    "budget_level": "moderate",
    "trip_type": "leisure"
  }'
```

### 5. List all your saved plans
```bash
curl http://localhost:8000/api/v1/plans \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## How to connect to frontend

In your frontend `.env.local` or Lovable env settings:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Every API call that needs auth must include:
```
Authorization: Bearer <token>
```

Store the token in `localStorage` after login:
```js
const res = await fetch('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({email, password}) })
const data = await res.json()
localStorage.setItem('token', data.access_token)
```

Use it in every request:
```js
const token = localStorage.getItem('token')
const res = await fetch('/api/v1/plans', {
  headers: { Authorization: `Bearer ${token}` }
})
```

---

## Common errors and fixes

| Error | Fix |
|---|---|
| `asyncpg.exceptions.InvalidPasswordError` | Wrong DATABASE_URL password |
| `could not translate host name` | Wrong DATABASE_URL host — copy from Neon dashboard |
| `401 Invalid or expired token` | Token expired — login again |
| `409 email already exists` | Use a different email |
| `ImportError: no module named asyncpg` | Run `pip install -r requirements.txt` |
