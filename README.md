# Basic RAG Chatbot – Backend API

A lightweight Flask backend that supports a Retrieval-Augmented Generation (RAG) pipeline: upload documents → extract → chunk → embed (FAISS) → retrieve → answer with LLM (OpenAI or Gemini) or smart fallbacks.

## Quick start (Windows)

- Requirements: Python 3.10+ recommended, PowerShell 5.1, internet for first-time model downloads.

```powershell
# From this folder
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Create .env (see template below), then run
python .\app.py
```

Server runs at: http://127.0.0.1:5000

## Environment (.env) template

```ini
# CORS
FRONTEND_ORIGIN=http://localhost:5173

# RAG tuning
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.4
MAX_CONTEXT_LENGTH=8000
DEVICE=cpu

# Vector store
VECTOR_DB_PATH=vectorstores/index.faiss

# LLM provider
LLM_PROVIDER=gemini  # or: openai
OPENAI_API_KEY=
GEMINI_API_KEY=YOUR_GEMINI_KEY
DEFAULT_MODEL=gemini-1.5-flash  # e.g. gpt-4o-mini for OpenAI
MAX_TOKENS=500
TEMPERATURE=0.2

# Runtime
DEBUG=false
LOG_LEVEL=INFO

# Security (optional)
API_KEY=changeme123
RATE_LIMIT_ASK_PER_MIN=60
RATE_LIMIT_UPLOAD_PER_MIN=10
RATE_LIMIT_DELETE_PER_MIN=30
```

Notes
- If LLM keys are not set, the app will fall back to a rule-based answer.
- For OpenAI set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and a valid `DEFAULT_MODEL`.

## Data directories
- `documents/raw/` – original uploads
- `documents/processed/` – extracted text (`.txt`)
- `documents/metadata/` – per-document JSON metadata
- `vectorstores/` – FAISS index and mapping files

These are created automatically when you upload.

## API Overview

Base URL: `http://127.0.0.1:5000`

- GET `/health` – liveness/readiness
- GET `/` – service info
- POST `/ask` – ask a question (RAG if indexed docs exist)
- POST `/upload` – upload a document (pdf, txt, docx)
- GET `/documents` – list processed documents
- DELETE `/documents/:document_id` – delete a document + its vectors
- GET `/rag/stats` – vector store + retrieval config
- GET `/rag/warmup` – preload embedding model

Global errors
- 404 → `{ "error": "Not found" }`
- 500 → `{ "error": "Internal server error" }`

---

## Endpoint details

### GET /health
Response 200
```json
{ "status": "ok", "version": "0.1.0" }
```

### GET /
Response 200
```json
{
    "name": "basic-rag-chatbot-backend",
    "version": "0.1.0",
    "endpoints": ["/health","/ask","/rag/warmup","/upload","/documents","/documents/<document_id>","/rag/stats"],
    "message": "Backend operational"
}
```

### POST /ask

Request (JSON)
```json
{ "question": "What projects has Jane worked on?", "document_id": "doc_abc123" }
```
- `document_id` is optional. If provided, fallback keyword search will only scan that document.
- Content-Type: `application/json` (otherwise 415)
- Errors: 400 if `question` is missing/empty

Success 200
```json
{
    "answer": "…",
    "sources": [
        { "document_id": "doc_123", "chunk_id": "c_5", "score": 0.78, "page": 3, "snippet": "…" }
    ],
    "meta": { "model": "gemini-1.5-flash", "has_sources": true, "tokens_used": 0, "context_length": 1477, "generation_time_ms": 2312 }
}
```

Notes on `sources`
- Retrieval sources: `{ document_id, chunk_id, score, page?, snippet }`
- Fallback sources (regex/keyword): `{ type: "file", path }`
Handle both in the UI.

### POST /upload
Multipart form-data
- Field name: `file`

Success 201
```json
{
    "message": "Uploaded and indexed",
    "document_id": "doc_123",
    "chunks_indexed": 42,
    "vector_store": { "total_vectors": 123, "index_type": "faiss_ip", "dim": 384 }
}
```

Errors
- 400: `{ "error": "No file part in request" }` or unsupported file
- 500: `{ "error": "<message>" }`

### GET /documents
Success 200
```json
{
    "documents": [
        {
            "document_id": "doc_123",
            "filename": "Resume.pdf",
            "file_size": 123456,
            "file_type": "application/pdf",
            "upload_time": "2025-09-11T12:34:56",
            "processed_time": "2025-09-11T12:35:20",
            "text_length": 9876,
            "chunk_count": 42,
            "status": "processed"
        }
    ]
}
```

### DELETE /documents/:document_id
Success 200 or Not found 404
```json
{
    "vectors_removed": 42,
    "message": "Deleted document doc_123",
    "vector_store": { "total_vectors": 81 }
}
```

### GET /rag/stats
Success 200
```json
{
    "status": "ok",
    "vector_store_stats": { "total_vectors": 123, "index_type": "faiss_ip", "dim": 384 },
    "config": { "top_k_results": 5, "similarity_threshold": 0.4, "max_context_length": 8000 }
}
```

### GET /rag/warmup
Success 200
```json
{
    "status": "ok",
    "device": "cpu",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "vector_store": { "total_vectors": 123 }
}
```

---

## Windows-friendly examples

### Upload (recommended)
```powershell
# Use curl.exe for multipart form uploads
curl.exe -X POST "http://127.0.0.1:5000/upload" -F "file=@D:\\Downloads\\Resume.pdf"
```

### Upload (PowerShell alternative)
```powershell
# In some environments, Invoke-RestMethod -Form works; if it fails, prefer curl.exe
Invoke-RestMethod -Uri "http://127.0.0.1:5000/upload" -Method Post -Form @{ file = Get-Item 'D:\\Downloads\\Resume.pdf' }
```

### Ask a question
```powershell
$body = @{ question = "Summarize the candidate's backend experience" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:5000/ask" -Method Post -ContentType 'application/json' -Body $body
```

Or with curl.exe
```powershell
curl.exe -H "Content-Type: application/json" -d "{\"question\":\"Summarize the candidate's backend experience\"}" http://127.0.0.1:5000/ask
```

### Stats and health
```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
Invoke-RestMethod http://127.0.0.1:5000/rag/stats
```

---

## Frontend integration notes
- Always send `Content-Type: application/json` to `/ask`.
- On `/ask`, support both `RetrievalSource` and fallback `FileSource` shapes.
- After `/upload` (201), refresh `/documents` and/or `/rag/stats`.
- Consider calling `/rag/warmup` once on app load to reduce first-answer latency.

Suggested TS types
```ts
export type RetrievalSource = {
    document_id: string;
    chunk_id: string;
    score: number;
    page?: number;
    snippet: string;
};
export type FileSource = { type: 'file'; path: string };
export type Source = RetrievalSource | FileSource;
export type AskRequest = { question: string };
export type AskResponse = { answer: string; sources: Source[]; meta: Record<string, any> };
export type UploadResponse = { message: string; document_id: string; chunks_indexed: number; vector_store: Record<string, any> };
export type DocItem = { document_id: string; filename: string; file_size: number; file_type: string; upload_time: string; processed_time?: string | null; text_length: number; chunk_count: number; status: string };
```

---

## Troubleshooting
- 415 on `/ask`: Ensure `Content-Type: application/json`.
- 400 on `/upload`: Ensure form field name is `file`. Use `curl.exe -F "file=@PATH"`.
- First call slow: Call `/rag/warmup` after server starts.
- Memory issues on Windows: Debug/reloader are disabled by default; keep `DEBUG=false`.
- No answers with sources: Check `/rag/stats` shows `total_vectors > 0`. If 0, upload and re-try.
- LLM not used: Verify `.env` has `LLM_PROVIDER`, API key, and a valid `DEFAULT_MODEL`.

---

## Security & Rate Limiting

API key (header `X-API-Key`) is enforced only if `API_KEY` is set in `.env`.

Protected endpoints:
- POST `/ask`
- POST `/upload`
- DELETE `/documents/:id`

Rate limiting uses `flask-limiter` (fixed one‑minute window per IP) with environment-driven limits:
```
RATE_LIMIT_ASK_PER_MIN=60
RATE_LIMIT_UPLOAD_PER_MIN=10
RATE_LIMIT_DELETE_PER_MIN=30
```
Set any to 0 (or omit) to disable that specific limit.

Optional distributed backend:
```
RATE_LIMIT_STORAGE_URI=redis://localhost:6379
```
Defaults to in-memory (`memory://`).

### Using Redis for Rate Limiting

1. Start Redis (Docker example):
```bash
docker run -d --name rag-redis -p 6379:6379 redis:7-alpine
```
2. Set in `.env`:
```ini
RATE_LIMIT_STORAGE_URI=redis://localhost:6379
```
3. Install deps (already in requirements): `redis`, `flask-limiter`.
4. Restart the backend.

If Redis becomes unreachable, flask-limiter will typically fall back or error—consider monitoring logs. For high availability use a managed Redis or sentinel cluster.

Exceeded response example:
```json
{
    "error": "429 Too Many Requests: Rate limit exceeded",
    "code": "RATE_LIMIT"
}
```

Unauthorized (wrong / missing API key):
```json
{ "error": "Unauthorized", "code": "API_KEY_INVALID" }
```

---

## License
Internal/demo use. Add your preferred license if distributing.
