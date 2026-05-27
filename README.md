# HR Policy Bot — Teams Tab

AI-powered HR policy assistant built as a Microsoft Teams personal tab. Uses RAG (Retrieval-Augmented Generation) with Azure AI Search, Azure OpenAI, and Azure Document Intelligence.

## Architecture

```
React (Vite) ──→ FastAPI ──→ Azure AI Search (hybrid retrieval)
                    │              ↕
                    │         Azure Blob Storage (parent sections)
                    │              ↕
                    └──→ Azure OpenAI GPT-4o (streaming answer)
```

## Repo Structure

```
hr-bot/
├── backend/          # FastAPI — RAG chat API with SSE streaming
├── frontend/         # React (Vite) — Chat UI
├── ingestion/        # Python pipeline — PDF → chunks → AI Search
├── teams-app/        # Teams manifest for sideloading
├── .env.example      # Template for required keys
└── README.md
```

## Local Development Quickstart

### 1. Configure Environment

```bash
cp .env.example backend/.env
# Edit backend/.env with your Azure service credentials
```

Conversational memory is handled in-process with LangChain windowed memory. No Redis setup is required for local development.

### 2. Ingestion Pipeline (run once to index HR documents)

```bash
cd ingestion
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create the AI Search index
python setup_index.py

# Ingest a PDF
python run_local.py ../sample-docs/leave-policy.pdf "https://yoursharepoint.com/leave-policy.pdf"
```

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 5. Verify

```bash
curl http://localhost:8000/api/health
# → {"status":"ok","checks":{"memory":"langchain_in_process"}}
```

Open http://localhost:5173 — the chat UI should load.

## Teams Sideloading

1. Start a tunnel: `devtunnel host -p 5173 --allow-anonymous`
2. Update `teams-app/manifest.json` with your tunnel URL
3. Zip `teams-app/` contents → upload as custom app in Teams

## Azure Services Required

| Service | Purpose |
|---------|---------|
| Azure OpenAI | GPT-4o chat + text-embedding-3-large |
| Azure AI Search | Hybrid vector + semantic search |
| Azure Blob Storage | Parent section storage |
| Azure Document Intelligence | PDF structure extraction |
| LangChain in-process memory | Session/conversation history |
# hr-bot
