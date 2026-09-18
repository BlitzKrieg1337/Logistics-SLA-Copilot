# Logistics SLA Copilot

🚀 **Live App:** [logistics-sla-copilot.vercel.app](https://logistics-sla-copilot.vercel.app)  
⚡ **API Health:** [logistics-sla-copilot.onrender.com/test](https://logistics-sla-copilot.onrender.com/test)

An AI-assisted operations copilot for investigating delivery delays, retrieving vendor SLA terms, calculating late-delivery penalties, researching possible Force Majeure events, and requesting human approval before a penalty is written to the ledger.

Built as a portfolio project to demonstrate agent orchestration, retrieval-augmented generation (RAG), database RBAC, and human-in-the-loop controls.

## What it can do

- Find delayed, delivered-late, and in-transit orders from PostgreSQL.
- Retrieve vendor-specific SLA clauses from Pinecone-hosted contract documents.
- Calculate billable delay days from contract grace periods and convert penalties to INR using live FX data.
- Search recent disruption news to provide Force Majeure context for a human decision.
- Pause before a ledger update so a user can explicitly approve or reject it.

## Architecture

```text
   React + Vite frontend
            |
         FastAPI API
            |
      LangGraph agent
  |       |       |       |
SQL     RAG     FX API   News API
  |       |       |       |
Postgres Pinecone Frankfurter Tavily
```

The LangGraph workflow separates ordinary analytical tools from the ledger-writing tool. It interrupts before `post_penalty_to_ledger` executes, and the frontend displays an approval card with Approve and Reject actions.

## Tech stack

- **Frontend:** React, Vite, Tailwind CSS, Axios
- **Backend:** FastAPI, Pydantic, Uvicorn
- **Agent:** LangGraph and LangChain, with OpenRouter, Groq, and Gemini model configuration
- **Data:** Neon/PostgreSQL, Pinecone, LangGraph `PostgresSaver`
- **External data:** Frankfurter FX API and Tavily news search
- **Testing and observability:** LangSmith evaluation and tracing

## Security and safety controls

- **Read/write separation:** analytics uses `READONLY_DATABASE_URL`; ledger updates use `UPDATEONLY_DATABASE_URL`.
- **Database RBAC:** `verify_rbac.py` validates that the read-only role cannot update records.
- **Read-only SQL tool:** only `SELECT` and `WITH ... SELECT` statements are accepted by the analytics tool.
- **Human approval:** a ledger update is interrupted before execution and requires a UI decision.
- **Guardrails:** hypothetical writes, batch ledger updates, destructive SQL, and unverified penalties are refused or escalated.

## Local setup

### Prerequisites

- Python 3.13+
- Node.js 20+
- A PostgreSQL/Neon database
- Pinecone, Tavily, and LLM-provider credentials

### 1. Install dependencies

```powershell
uv sync
cd frontend
npm install
cd ..
```

### 2. Configure environment variables

Create a `.env` file in the project root. Never commit it.

```env
# LangGraph state database
DATABASE_URL=postgresql://...

# Application database roles
READONLY_DATABASE_URL=postgresql://...
UPDATEONLY_DATABASE_URL=postgresql://...

# Used only when running src/scripts/init_db.py
READONLY_ROLE=...
READONLY_PASSWORD=...
UPDATE_ROLE=...
UPDATE_PASSWORD=...

# Retrieval, news, tracing, and model providers
PINECONE_API_KEY=...
TAVILY_API_KEY=...
LANGSMITH_API_KEY=...
OPENROUTER_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...

# Local frontend origin; add the deployed frontend origin after deployment
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Create `frontend/.env` when the frontend should call a non-local API:

```env
VITE_API_BASE=https://your-api-domain.example
```

### 3. Initialize services

Run these when provisioning a new database or Pinecone index:

```powershell
uv run python src/scripts/init_db.py
uv run python verify_rbac.py
uv run python src/scripts/ingest_contracts.py
```

### 4. Run locally

Start the API:

```powershell
uv run uvicorn src.api.main:app --reload
```

In a separate terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open the local Vite URL shown in the terminal, normally `http://localhost:5173`.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/test` | Health check |
| `POST` | `/chat` | Send a message for a conversation thread |
| `POST` | `/action` | Approve or reject a pending ledger action |
| `GET` | `/history/{thread_id}` | Restore conversation history and pending approval state |

## Evaluation

The evaluation suite uses a fresh LangGraph thread for each case, preventing one benchmark from leaking messages or tool calls into another.

```powershell
uv run python evals/create_eval_dataset.py
uv run python evals/run_eval.py
```

It covers normal SQL retrieval, contract grounding, multi-tool investigation, destructive SQL refusal, hypothetical and batch write refusal, missing-order handling, Force Majeure escalation, and the ledger approval boundary.

## Deployment checklist

1. Deploy the FastAPI backend with a command equivalent to:

   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
   ```

2. Set the backend environment variables in the hosting provider’s secret manager.
3. Deploy `frontend` as a Vite application.
4. Set `VITE_API_BASE` to the deployed backend URL during the frontend build.
5. Set `CORS_ORIGINS` in the backend to the exact deployed frontend origin.
6. Verify `/test`, a read-only question, a contract lookup, and the approval flow before sharing the application.

## Limitations

- Contract retrieval, FX rates, and news results rely on external services and can change over time.
- Force Majeure qualification is a human/legal decision; the copilot provides evidence, not a legal determination.
- This portfolio project does not yet include application-level authentication or multi-tenant authorization.