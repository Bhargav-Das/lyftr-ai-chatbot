# 🚀 Lyftr AI — Resilient Multi-Key AI Chatbot

A production-ready AI chatbot built with **FastAPI, React, Gemini, SQLite, Docker, Render, and Vercel**, designed around reliability and graceful failure handling.

Lyftr AI goes beyond a basic chatbot by implementing **automatic API-key failover, response caching, persistent conversation history, failure simulation, automated API testing, Dockerized deployment, and production hosting**.

---

## 🌐 Live Application

### Frontend

**Vercel:**  
https://lyftr-ai-chatbot-ivory.vercel.app

### Backend API

**Render:**  
https://lyftr-ai-chatbot-backend-opx0.onrender.com

### Swagger API Documentation

https://lyftr-ai-chatbot-backend-opx0.onrender.com/docs

### Health Check

https://lyftr-ai-chatbot-backend-opx0.onrender.com/health

> The backend is hosted on a free Render instance. After a period of inactivity, the first request may take additional time while the service wakes up.

---

# 📌 Project Overview

Lyftr AI is a resilient full-stack AI chatbot that communicates with Google's Gemini models through a FastAPI backend.

The system is designed to remain functional when an AI provider request fails. Instead of immediately returning an error, the backend can automatically attempt another configured API key.

The application also maintains conversation history, caches repeated inference requests, exposes diagnostic metadata, and provides controlled failure simulation for testing resilience.

---

# ✨ Key Features

### 🤖 Gemini AI Integration

The backend integrates with Gemini through LiteLLM and currently uses:

```text
gemini/gemini-3.5-flash-lite
```

The model can be changed through configuration without modifying the frontend.

---

### 🔄 Automatic API-Key Failover

Multiple Gemini API keys can be configured.

Normal request:

```text
Request
   ↓
Key 1
   ↓
Gemini
   ↓
Response
```

When the first key fails:

```text
Request
   ↓
Key 1
   ↓
429 / Provider Failure
   ↓
Automatic Failover
   ↓
Key 2
   ↓
Gemini
   ↓
Successful Response
```

The response metadata exposes information such as:

```json
{
  "resolution_source": "LIVE_INFERENCE",
  "key_id": "key_2",
  "fallback_attempts": 1
}
```

This makes failover behavior observable and easy to verify.

---

### 🧪 Controlled Failure Simulation

The API supports controlled provider-failure simulation through the:

```text
X-Simulate-Failure
```

HTTP header.

Example:

```text
X-Simulate-Failure: key_1=429
```

This allows the failover mechanism to be tested without intentionally damaging or disabling a real API key.

A production test confirmed:

```text
key_1 → simulated 429 failure
key_2 → successful inference
fallback_attempts → 1
HTTP status → 200 OK
```

---

### ⚡ LLM Response Caching

Repeated equivalent inference requests can be served from cache instead of contacting Gemini again.

First request:

```text
User
 ↓
Backend
 ↓
Gemini
 ↓
Response
 ↓
Cache
```

Repeated request:

```text
User
 ↓
Backend
 ↓
LLM Cache
 ↓
Response
```

Cached responses expose:

```json
{
  "resolution_source": "LLM_CACHE",
  "key_id": null,
  "fallback_attempts": 0
}
```

This can reduce unnecessary model calls and improve response time for repeated requests.

---

### 💾 Persistent Conversation Sessions

Conversation messages are persisted using SQLite.

Each conversation uses a unique:

```text
session_id
```

Previous messages are loaded before a new inference request, allowing the model to understand earlier conversation context.

Example:

```text
User:
Explain Docker in one sentence.

Assistant:
Docker is a tool that packages applications and their
dependencies into portable containers.

User:
What did I just ask you about?

Assistant:
You just asked me to explain Docker in one sentence.
```

This demonstrates multi-turn conversational context.

---

### 📊 Response Metadata

AI responses include operational metadata for observability.

Example:

```json
{
  "session_id": "example-session",
  "reply": "The capital of Japan is Tokyo.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 537,
    "input_tokens": 15,
    "output_tokens": 7,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

Metadata can indicate:

- Resolution source
- Model used
- Request latency
- Input tokens
- Output tokens
- API key identifier
- Number of fallback attempts

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │        User         │
                         └──────────┬──────────┘
                                    │
                                    │ HTTPS
                                    ▼
                     ┌───────────────────────────┐
                     │       React / Vite        │
                     │     Vercel Frontend       │
                     └─────────────┬─────────────┘
                                   │
                                   │ REST API
                                   ▼
                     ┌───────────────────────────┐
                     │          FastAPI          │
                     │      Render Backend       │
                     └─────────────┬─────────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
        ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
        │ Session History│ │  LLM Cache   │ │ Failure Parser │
        │     SQLite     │ │              │ │                │
        └────────────────┘ └──────┬───────┘ └────────────────┘
                                  │
                                  │ Cache Miss
                                  ▼
                         ┌──────────────────┐
                         │      Key 1       │
                         └────────┬─────────┘
                                  │
                         Failure? │
                           ┌──────┴──────┐
                           │             │
                          No            Yes
                           │             │
                           │             ▼
                           │    ┌──────────────────┐
                           │    │      Key 2       │
                           │    └────────┬─────────┘
                           │             │
                           └──────┬──────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   Gemini Model   │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │     Response     │
                         │    + Metadata    │
                         └──────────────────┘
```

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Frontend Build Tool | Vite |
| Backend | FastAPI |
| Language | Python |
| AI Provider | Google Gemini |
| LLM Integration | LiteLLM |
| Database | SQLite |
| Async Database Access | aiosqlite |
| HTTP Client | httpx |
| Validation | Pydantic |
| Testing | pytest / pytest-asyncio |
| Containerization | Docker |
| Multi-container Orchestration | Docker Compose |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| API Documentation | Swagger / OpenAPI |

---

# 📁 Project Structure

```text
lyftr-ai-chatbot/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── llm_service.py
│   │   ├── main.py
│   │   └── schemas.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py
│   │
│   ├── .dockerignore
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

---

# 🔌 API Endpoints

## Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

---

## Chat

```http
POST /chat
```

Example request:

```json
{
  "session_id": "demo-session-001",
  "message": "What is the capital of Japan?"
}
```

Example response:

```json
{
  "session_id": "demo-session-001",
  "reply": "The capital of Japan is Tokyo.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 537,
    "input_tokens": 15,
    "output_tokens": 7,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

---

## Retrieve Session Messages

```http
GET /sessions/{session_id}/messages
```

Returns the persisted conversation associated with a session.

---

# ⚙️ Environment Variables

Create a local `.env` file based on `.env.example`.

Example:

```env
LLM_API_KEYS=your_gemini_api_key_1,your_gemini_api_key_2
LLM_MODEL=gemini/gemini-3.5-flash-lite

DATABASE_URL=sqlite:///./app.db

ALLOWED_ORIGINS=http://localhost:3000

ENABLE_FAILURE_SIMULATION=true
```

> **Never commit real API keys or `.env` files to GitHub.**

The repository `.gitignore` should exclude secret environment files.

For production, secrets should be configured directly through the hosting provider's environment-variable settings.

---

# 💻 Local Development

## 1. Clone the Repository

```bash
git clone https://github.com/Bhargav-Das/lyftr-ai-chatbot.git
cd lyftr-ai-chatbot
```

---

## 2. Backend Setup

Move into the backend:

```bash
cd backend
```

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure `.env`, then start FastAPI:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

Health:

```text
http://localhost:8000/health
```

---

# 🎨 Frontend Setup

From the repository root:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Configure the frontend API URL if required:

```env
VITE_API_URL=http://localhost:8000
```

Start Vite:

```bash
npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# 🐳 Docker Deployment

The project includes Docker support for both the frontend and backend.

From the repository root:

```bash
docker compose build
```

Start the complete stack:

```bash
docker compose up
```

Or build and start together:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop containers:

```bash
docker compose down
```

After startup:

```text
Frontend → http://localhost:3000
Backend  → http://localhost:8000
Swagger  → http://localhost:8000/docs
```

---

# 🧪 Automated Testing

Backend tests are implemented with `pytest`.

From:

```text
backend/
```

run:

```bash
pytest -v
```

Verified test result:

```text
9 passed
```

The automated suite verifies important API behavior including:

```text
test_health
test_empty_message_returns_422
test_empty_session_id_returns_422
test_message_too_long_returns_422
test_unknown_session_returns_404
test_all_provider_failure_returns_503
test_successful_chat_is_persisted
test_multi_turn_history_sent_to_llm
test_key_1_failure_falls_back_to_key_2
```

These tests cover validation, health monitoring, provider failure handling, persistence, conversation history, and automatic failover.

---

# 🛡️ Failure Handling

When all configured providers/keys fail, the backend returns:

```http
503 Service Unavailable
```

Example:

```json
{
  "detail": "all providers unavailable"
}
```

This prevents internal provider exceptions from being exposed directly to API clients.

---

# 🧠 Conversation Flow

For every chat request, the backend:

```text
1. Receives session_id + message
                ↓
2. Retrieves previous session messages
                ↓
3. Constructs conversation context
                ↓
4. Checks inference/cache path
                ↓
5. Attempts Gemini inference
                ↓
6. Falls back to another key when required
                ↓
7. Generates response metadata
                ↓
8. Stores successful user + assistant messages
                ↓
9. Returns response to frontend
```

Messages are stored only after successful inference, preventing failed requests from polluting conversation history.

---

# 🚦 Production Verification

The deployed application has been manually verified for the following scenarios.

| Test | Result |
|---|---|
| Backend health endpoint | ✅ Passed |
| Live Gemini inference | ✅ Passed |
| Frontend → backend communication | ✅ Passed |
| Conversation context | ✅ Passed |
| SQLite session persistence | ✅ Passed |
| Key 1 → Key 2 failover | ✅ Passed |
| Simulated HTTP 429 | ✅ Passed |
| LLM cache hit | ✅ Passed |
| Production CORS | ✅ Passed |
| Docker deployment | ✅ Passed |
| Automated backend tests | ✅ 9/9 Passed |
| Render deployment | ✅ Live |
| Vercel deployment | ✅ Live |

---

# 🌍 Production Architecture

```text
                  INTERNET
                      │
                      ▼
        ┌─────────────────────────┐
        │         Vercel          │
        │   React/Vite Frontend   │
        └────────────┬────────────┘
                     │
                     │ HTTPS API
                     ▼
        ┌─────────────────────────┐
        │         Render          │
        │     FastAPI Backend     │
        └────────────┬────────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
       SQLite      Cache     Failover
                               │
                         ┌─────┴─────┐
                         ▼           ▼
                       Key 1       Key 2
                         │           │
                         └─────┬─────┘
                               ▼
                         Gemini API
```

---

# 🔐 Security Considerations

The project follows several basic security practices:

- API keys are stored in environment variables.
- `.env` files are excluded from Git.
- Production secrets are managed through hosting environment variables.
- CORS can be restricted to the deployed frontend domain.
- Internal provider exceptions are converted into safe API responses.
- Failure simulation can be controlled through configuration.
- Real secret values are never required in source code.

---

# 📈 Resilience Strategy

The primary resilience mechanism is multi-key failover.

For example:

```text
Request
   │
   ▼
API Key 1
   │
   ├── Success ───────────────► Return response
   │
   └── Failure / 429
              │
              ▼
          API Key 2
              │
              ├── Success ────► Return response
              │
              └── Failure ────► 503 Service Unavailable
```

This design prevents a single API-key/provider failure from immediately making the chatbot unavailable.

---

# 📦 Deployment

## Backend — Render

The FastAPI backend is deployed on Render using the backend Docker configuration.

Production backend:

```text
https://lyftr-ai-chatbot-backend-opx0.onrender.com
```

---

## Frontend — Vercel

The React/Vite application is deployed independently on Vercel.

Production frontend:

```text
https://lyftr-ai-chatbot-ivory.vercel.app
```

The frontend uses:

```env
VITE_API_URL=https://lyftr-ai-chatbot-backend-opx0.onrender.com
```

to communicate with the production backend.

---

# 🔮 Possible Future Improvements

Potential improvements include:

- Redis-based distributed caching
- PostgreSQL for production persistence
- User authentication
- Rate limiting
- Streaming LLM responses
- Structured logging
- Prometheus metrics
- Grafana monitoring
- CI/CD with GitHub Actions
- Additional AI-provider fallback
- Cloud-managed database
- Kubernetes deployment
- Horizontal backend scaling

---

# 🎯 What This Project Demonstrates

This project demonstrates practical knowledge of:

- Full-stack application development
- REST API design
- FastAPI
- React
- LLM API integration
- Multi-key failover
- Fault tolerance
- Caching
- Persistent conversational context
- Asynchronous Python
- API validation
- Automated testing
- Docker
- Docker Compose
- Environment/secrets management
- Cloud deployment
- Production frontend/backend integration

---

# 👨‍💻 Author

**Bhargav Das**

GitHub:  
https://github.com/Bhargav-Das

Project Repository:  
https://github.com/Bhargav-Das/lyftr-ai-chatbot

---

## ⭐ Lyftr AI

**A resilient AI chatbot designed to keep responding even when individual inference paths fail.**