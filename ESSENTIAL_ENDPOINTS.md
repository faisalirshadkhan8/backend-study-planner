# Essential API Endpoints

This document provides a prioritized list of endpoints for the RAG Chatbot backend, organized by importance for different use cases.

## 🔴 MUST-HAVE Endpoints (Core Functionality)

These endpoints are **essential** for basic chatbot functionality. Your frontend must implement these to have a working application.

### 1. POST /upload
**Purpose**: Upload documents (PDF, DOCX, TXT) for processing and indexing.

**Why Essential**: Without this, users cannot add documents to the knowledge base.

**Request**:
```typescript
// multipart/form-data
{
  file: File  // field name MUST be "file"
}
```

**Response**:
```typescript
{
  message: string,
  document_id: string,
  filename: string,
  chunks_indexed: number,
  vector_store_stats: {
    total_documents: number,
    total_vectors: number
  }
}
```

**Example**:
```typescript
const formData = new FormData();
formData.append('file', file);

const response = await fetch('http://127.0.0.1:5000/upload', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'  // if API_KEY is set
  },
  body: formData
});
```

---

### 2. POST /ask
**Purpose**: Ask questions about the uploaded documents.

**Why Essential**: This is the core RAG functionality - querying documents and getting AI-generated answers.

**Request**:
```typescript
{
  question: string,
  document_id?: string  // Optional: scope query to specific document
                       // If omitted, uses active document (if set) or all documents
}
```

**Response**:
```typescript
{
  answer: string,
  sources: Array<{
    type: "retrieval" | "fallback" | "file",
    document_id?: string,
    chunk_id?: string,
    text?: string,
    similarity?: number,
    path?: string
  }>,
  meta: {
    model: string,
    has_sources: boolean,
    token_count?: number
  }
}
```

**Example**:
```typescript
const response = await fetch('http://127.0.0.1:5000/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'  // if API_KEY is set
  },
  body: JSON.stringify({
    question: "What is the main topic of the document?"
  })
});
```

---

### 3. GET /documents
**Purpose**: List all uploaded documents with metadata.

**Why Essential**: Users need to see what documents are available and select which one to query.

**Response**:
```typescript
{
  documents: Array<{
    document_id: string,
    filename: string,
    file_size: number,
    file_type: string,
    upload_time: string,
    processed_time: string,
    text_length: number,
    chunk_count: number,
    status: "uploaded" | "processed" | "indexed" | "error"
  }>,
  total: number
}
```

**Example**:
```typescript
const response = await fetch('http://127.0.0.1:5000/documents');
const data = await response.json();
console.log(`Total documents: ${data.total}`);
```

---

### 4. DELETE /documents/{document_id}
**Purpose**: Remove a document and its vectors from the system.

**Why Essential**: Users need to manage their documents (remove outdated or irrelevant files).

**Response**:
```typescript
{
  message: string,
  document_id: string,
  vectors_removed: number
}
```

**Example**:
```typescript
const response = await fetch(`http://127.0.0.1:5000/documents/${docId}`, {
  method: 'DELETE',
  headers: {
    'X-API-Key': 'your-api-key'  // if API_KEY is set
  }
});
```

---

## 🟡 RECOMMENDED Endpoints (Enhanced UX)

These endpoints significantly improve user experience and should be implemented once core functionality is working.

### 5. POST /active-document
**Purpose**: Set the "active document" for the current session.

**Why Recommended**: Simplifies frontend logic - set active document once (on upload or selection), then all `/ask` queries automatically scope to it without passing `document_id` every time.

**Request**:
```typescript
{
  document_id: string | null  // null to clear active document
}
```

**Response**:
```typescript
{
  message: "Active document set" | "Active document cleared",
  document_id?: string
}
```

**Usage Pattern**:
```typescript
// 1. Upload document
const uploadResponse = await fetch('/upload', { /* ... */ });
const { document_id } = await uploadResponse.json();

// 2. Set as active
await fetch('/active-document', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ document_id })
});

// 3. Ask questions without specifying document_id
await fetch('/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: "What is this about?" })
  // Automatically uses active document!
});
```

---

### 6. GET /active-document
**Purpose**: Check which document is currently active for the session.

**Why Recommended**: Helps UI display current context and synchronize state after page refresh.

**Response**:
```typescript
{
  document_id: string | null
}
```

**Example**:
```typescript
const response = await fetch('http://127.0.0.1:5000/active-document');
const { document_id } = await response.json();
if (document_id) {
  console.log(`Active document: ${document_id}`);
}
```

---

### 7. GET /health
**Purpose**: Check if backend is running and responsive.

**Why Recommended**: Essential for production monitoring, helpful for debugging connection issues during development.

**Response**:
```typescript
{
  status: "healthy",
  timestamp: string
}
```

**Example**:
```typescript
// Check backend health on app startup
const response = await fetch('http://127.0.0.1:5000/health');
if (response.ok) {
  console.log('Backend is healthy');
}
```

---

## 🟢 OPTIONAL Endpoints (Advanced Features)

These endpoints are useful for specific use cases but not required for basic functionality.

### 8. GET /documents/{document_id}/content
**Purpose**: Retrieve full text content of a document (with optional truncation).

**Use Cases**:
- Document preview
- Citation generation
- Full-text search in frontend
- Debugging retrieval results

**Query Parameters**:
- `max_length`: Maximum characters to return (default: 5000)

**Response**:
```typescript
{
  document_id: string,
  filename: string,
  content: string,
  metadata: {
    file_type: string,
    file_size: number,
    text_length: number,
    truncated: boolean
  }
}
```

---

### 9. GET /rag/stats
**Purpose**: Get statistics about the RAG system (documents, vectors, embeddings).

**Use Cases**:
- Admin dashboard
- System monitoring
- Debugging indexing issues

**Response**:
```typescript
{
  version: string,
  documents_count: number,
  embedding_model: string,
  vector_store_stats: {
    total_documents: number,
    total_vectors: number,
    embedding_dimension: number
  }
}
```

---

### 10. POST /rag/warmup
**Purpose**: Pre-load embedding model to reduce first-query latency.

**Use Cases**:
- Call on app startup to avoid 10-30s delay on first query
- Production optimization

**Response**:
```typescript
{
  message: string,
  model: string,
  embedding_dimension: number,
  warmup_time_ms: number
}
```

**Example**:
```typescript
// Call on app initialization
fetch('http://127.0.0.1:5000/rag/warmup', { method: 'POST' })
  .then(() => console.log('Embedding model preloaded'));
```

---

## Implementation Priority

### Phase 1: Minimal Viable Product (MVP)
**Endpoints**: `/upload`, `/ask`, `/documents`, `DELETE /documents/{id}`

This gives you:
- ✅ Upload documents
- ✅ Ask questions
- ✅ View document list
- ✅ Delete documents

### Phase 2: Enhanced UX
**Add**: `/active-document` (POST/GET), `/health`

This adds:
- ✅ Simplified querying (active document pattern)
- ✅ Health monitoring

### Phase 3: Advanced Features
**Add**: `/documents/{id}/content`, `/rag/stats`, `/rag/warmup`

This adds:
- ✅ Document preview
- ✅ System statistics
- ✅ Performance optimization

---

## Quick Start Example (MVP)

Here's a complete flow using only the essential endpoints:

```typescript
// 1. Upload a document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadRes = await fetch('http://127.0.0.1:5000/upload', {
  method: 'POST',
  body: formData
});
const { document_id } = await uploadRes.json();

// 2. List documents
const listRes = await fetch('http://127.0.0.1:5000/documents');
const { documents } = await listRes.json();
console.log('Available documents:', documents);

// 3. Ask a question
const askRes = await fetch('http://127.0.0.1:5000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'What is the main topic?',
    document_id  // Optional: scope to specific document
  })
});
const { answer, sources } = await askRes.json();
console.log('Answer:', answer);

// 4. Delete document when done
await fetch(`http://127.0.0.1:5000/documents/${document_id}`, {
  method: 'DELETE'
});
```

---

## Error Handling

All endpoints may return these common errors:

- **400 Bad Request**: Invalid input (missing required fields, invalid JSON)
- **401 Unauthorized**: Missing or invalid API key (when `API_KEY` env is set)
- **404 Not Found**: Document not found (for document-specific endpoints)
- **415 Unsupported Media Type**: Wrong `Content-Type` header (should be `application/json` for JSON endpoints)
- **429 Too Many Requests**: Rate limit exceeded (see headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- **500 Internal Server Error**: Server-side error (check backend logs)

**Rate Limits** (default):
- `/ask`: 60 requests per minute
- `/upload`: 10 requests per minute
- `DELETE /documents/{id}`: 30 requests per minute

---

## Notes

- **Session Management**: Active document tracking uses `request.remote_addr` (client IP) as session key. In production with load balancers or proxies, consider using proper session tokens.
- **API Key**: Set `API_KEY` environment variable to require authentication for protected endpoints (`/upload`, `DELETE`).
- **CORS**: Backend enables CORS for all origins in development. Configure `CORS_ORIGINS` for production.
- **Field Names**: Upload endpoint requires field name `"file"` exactly - don't use custom names.
