# Craveful AI Restaurant Agent

A full-stack restaurant ordering demo built with React, FastAPI, and LangGraph. It combines a conversational ordering flow with an in-stock menu recommendation pipeline and a visible specialist-agent trace.

> **Demo notice:** This project simulates kitchen and service outcomes. It does not submit real orders, accept payments, or contact a restaurant.

## Features

- Browse and search a 24-item menu with live stock from the backend, including a vegetarian Chinese collection with momos, dumplings, spring rolls, fried rice, and chilli paneer.
- Create chat sessions, submit multiple cart items, check availability, and accept partial quantities.
- Reserve inventory atomically when an order quantity is confirmed. Successful completion consumes stock; a failed simulated kitchen/service flow returns its reservation.
- Recommend menu items by natural-language preferences using local TF-IDF cosine retrieval over descriptions, categories, and tags.
- Apply in-stock, dietary, spice-level, and USD price filters before the LLM writes a recommendation.
- Reject INR budget comparisons with a clear USD clarification rather than silently treating rupees as dollars.
- Use a LangGraph supervisor to route work to menu RAG, inventory, kitchen, and service nodes.
- Expose and display the agent trace and retrieved recommendations in the chat/API response.
- Retry simulated cooking/service failures and release the stock reservation when retries are exhausted.

## Architecture

```text
React + Vite
   │ REST (/api)
   ▼
FastAPI ── LangGraph supervisor
              ├── Menu RAG ── local TF-IDF retrieval ── Groq response
              ├── Inventory ── atomic in-process reservation
              ├── Kitchen ── simulated cooking/retry
              └── Service ── simulated serving/retry
```

RAG is implemented in `backend/menu_rag.py`. The menu corpus is a small Python catalog, so it is indexed and ranked locally at query time; no Chroma service, embedding model download, or separate vector database is required. The catalog's prices use USD, matching the storefront.

The new vegetarian Chinese dish photos are matched to their dishes and include visible creator and license credits where required.

## Requirements

- Python 3.12+
- Node.js and npm
- A Groq API key for live LLM-backed chat, ordering, and generated recommendations

## Run locally (Windows PowerShell)

Create `backend/.env` with your key (do not commit it):

```dotenv
GROQ_API_KEY=your_groq_api_key
```

Install backend dependencies and start the API:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api:app --reload
```

In another terminal, install and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). Vite proxies `/api` to `http://127.0.0.1:8000`. For a separately hosted frontend, set `VITE_API_BASE_URL` to the API origin and configure the API's `FRONTEND_ORIGINS`.

## Verify

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q backend\test_scenarios.py
Push-Location frontend
npm run build
Pop-Location
```

The backend tests cover order retries, stock checks, reservations, concurrent overselling protection, partial orders, failed-order refunds, RAG filters, currency handling, API sessions, and CORS.

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service health |
| `GET` | `/api/menu` | Current menu stock |
| `POST` | `/api/chat/sessions` | Create a conversation session |
| `POST` | `/api/sessions/{session_id}/messages` | Send a chat message |
| `POST` | `/api/checkout` | Start one conversation per cart item |

Chat and order responses include `agent_trace`, `recommendations`, order state, retry counts, and the quantity reserved for the current order.

## Demo scope and deployment notes

- Kitchen/service outcomes are intentionally simulated and randomized; the retry behavior can be made deterministic in tests by providing scripted outcomes.
- Stock reservations are atomic between requests handled by the **same Python process**, but stock is held in memory. Restarting the backend resets inventory, and multiple worker processes do not share a common stock ledger. Use a transactional shared database (for example PostgreSQL) before deploying for real concurrent ordering.
- The demo has no payment processor, delivery integration, real kitchen system, authentication, or persistent conversation store.
- Requests with INR budgets are asked to use USD. No exchange rate or currency conversion is applied.
- The Groq key is needed for LLM paths; the local retriever itself requires no external embedding API.
