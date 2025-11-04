# Frontend API Integration Guide

Complete reference for integrating the RAG chatbot backend with your React frontend.

## Base Configuration

```typescript
// API Configuration
const API_BASE_URL = 'http://127.0.0.1:5000';
const API_KEY = 'your_api_key_here'; // If API_KEY is set in backend .env

// Headers for protected endpoints
const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
};
```

## TypeScript Types

```typescript
// Request Types
export interface AskRequest {
  question: string;
  document_id?: string; // Optional: limit to specific document
                        // If omitted, uses active document (if set)
}

export interface SetActiveDocumentRequest {
  document_id: string | null; // null to clear active document
}

// Response Types
export interface RetrievalSource {
  document_id: string;
  chunk_id: string;
  score: number;
  page?: number;
  snippet: string;
}

export interface FileSource {
  type: 'file';
  path: string;
}

export type Source = RetrievalSource | FileSource;

export interface AskResponse {
  answer: string;
  sources: Source[];
  meta: {
    model: string;
    has_sources?: boolean;
    tokens_used?: number;
    context_length?: number;
    generation_time_ms?: number;
    latency_ms?: number;
    source_count?: number;
  };
}

export interface HealthResponse {
  status: 'ok';
  version: string;
}

export interface UploadResponse {
  message: string;
  document_id: string;
  chunks_indexed: number;
  vector_store: {
    total_vectors: number;
    index_type: string;
    dim: number;
  };
}

export interface DocumentMetadata {
  document_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  upload_time: string; // ISO 8601
  processed_time: string | null; // ISO 8601
  text_length: number;
  chunk_count: number;
  status: string;
}

export interface DocumentsResponse {
  documents: DocumentMetadata[];
}

export interface DeleteResponse {
  vectors_removed: number;
  message: string;
  vector_store: {
    total_vectors: number;
  };
}

export interface DocumentContentResponse {
  document_id: string;
  content: string;
  full_length: number;
  truncated: boolean;
  metadata: Record<string, any>;
}

export interface ErrorResponse {
  error: string;
  code?: string;
}
```

## API Endpoints

### 1. POST /ask

Ask a question with optional document scope.

**Note**: If you don't provide `document_id`, the backend will automatically use the active document (if one is set via `/active-document`). This simplifies your frontend - just set the active document once and all queries will scope to it.

**Request:**
```typescript
const askQuestion = async (question: string, documentId?: string): Promise<AskResponse> => {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ question, document_id: documentId })
  });
  
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};
```

**Example:**
```typescript
// Ask using active document (recommended)
const response = await askQuestion("What are the main findings?");

// Ask only within specific document (explicit override)
const response = await askQuestion(
  "What is question 1?",
  "Assignment1_SCD_20251103_123456"
);
```

**Response (200):**
```json
{
  "answer": "The main findings are...",
  "sources": [
    {
      "document_id": "doc_123",
      "chunk_id": "c_5",
      "score": 0.85,
      "page": 3,
      "snippet": "According to the research..."
    }
  ],
  "meta": {
    "model": "gemini-1.5-flash",
    "has_sources": true,
    "context_length": 1250,
    "generation_time_ms": 2100
  }
}
```

---

### 2. POST /active-document

Set the active document for the current session. All subsequent `/ask` queries (without explicit `document_id`) will automatically scope to this document.

**Request:**
```typescript
const setActiveDocument = async (documentId: string | null): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/active-document`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ document_id: documentId })
  });
  
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
};
```

**Example:**
```typescript
// Set active document after upload
await setActiveDocument("doc_abc123");

// Clear active document (queries will search all documents)
await setActiveDocument(null);
```

**Response (200):**
```json
{
  "message": "Active document set",
  "document_id": "doc_abc123"
}
```
```json
{
  "message": "Active document cleared"
}
```

---

### 3. GET /active-document

Get the currently active document for this session.

**Request:**
```typescript
const getActiveDocument = async (): Promise<string | null> => {
  const response = await fetch(`${API_BASE_URL}/active-document`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  return data.document_id;
};
```

**Example:**
```typescript
const activeDocId = await getActiveDocument();
if (activeDocId) {
  console.log(`Current active document: ${activeDocId}`);
} else {
  console.log('No active document set');
}
```

**Response (200):**
```json
{
  "document_id": "doc_abc123"
}
```
```json
{
  "document_id": null
}
```

---

### 4. POST /upload---

### 2. GET /health

Check backend health and version.

**Request:**
```typescript
const checkHealth = async (): Promise<HealthResponse> => {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
};
```

**Response (200):**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### 3. POST /upload

Upload a document (PDF, DOCX, TXT).

**Request:**
```typescript
const uploadDocument = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY // Don't set Content-Type, browser sets it automatically
    },
    body: formData
  });
  
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};
```

**HTML Example:**
```html
<input type="file" id="fileInput" accept=".pdf,.docx,.txt" />
<button onclick="handleUpload()">Upload</button>

<script>
async function handleUpload() {
  const input = document.getElementById('fileInput');
  const file = input.files[0];
  if (!file) return;
  
  try {
    const result = await uploadDocument(file);
    console.log('Uploaded:', result.document_id);
    alert(`Success! Indexed ${result.chunks_indexed} chunks`);
  } catch (err) {
    alert('Upload failed: ' + err.message);
  }
}
</script>
```

**Response (201):**
```json
{
  "message": "Uploaded and indexed",
  "document_id": "Assignment1_SCD_20251103_194523_a3f4d8e2",
  "chunks_indexed": 42,
  "vector_store": {
    "total_vectors": 123,
    "index_type": "faiss_ip",
    "dim": 384
  }
}
```

**Errors:**
- 400: `{"error": "No file part in request"}` - field name must be `file`
- 400: `{"error": "Unsupported file type"}` - only PDF/DOCX/TXT allowed
- 401: `{"error": "Unauthorized", "code": "API_KEY_INVALID"}` - wrong API key

---

### 4. GET /documents

List all uploaded documents.

**Request:**
```typescript
const listDocuments = async (): Promise<DocumentsResponse> => {
  const response = await fetch(`${API_BASE_URL}/documents`);
  return response.json();
};
```

**Response (200):**
```json
{
  "documents": [
    {
      "document_id": "Assignment1_SCD_20251103_194523_a3f4d8e2",
      "filename": "Assignment1_SCD.pdf",
      "file_size": 245678,
      "file_type": "application/pdf",
      "upload_time": "2025-11-03T19:45:23",
      "processed_time": "2025-11-03T19:45:28",
      "text_length": 12345,
      "chunk_count": 42,
      "status": "processed"
    }
  ]
}
```

---

### 5. DELETE /documents/:id

Delete a document and its vectors.

**Request:**
```typescript
const deleteDocument = async (documentId: string): Promise<DeleteResponse> => {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: 'DELETE',
    headers: {
      'X-API-Key': API_KEY
    }
  });
  
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};
```

**Response (200 or 404):**
```json
{
  "vectors_removed": 42,
  "message": "Deleted document Assignment1_SCD_20251103_194523_a3f4d8e2",
  "vector_store": {
    "total_vectors": 81
  }
}
```

---

### 6. GET /documents/:id/content (Optional)

Get document text content for preview or citation.

**Request:**
```typescript
const getDocumentContent = async (
  documentId: string,
  maxLength: number = 5000
): Promise<DocumentContentResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/documents/${documentId}/content?max_length=${maxLength}`
  );
  
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
};
```

**Response (200):**
```json
{
  "document_id": "Assignment1_SCD_20251103_194523_a3f4d8e2",
  "content": "Full extracted text of the document...",
  "full_length": 12345,
  "truncated": false,
  "metadata": {
    "filename": "Assignment1_SCD.pdf",
    "upload_time": "2025-11-03T19:45:23"
  }
}
```

---

## Common Patterns

### Complete Upload → Ask Flow

```typescript
async function uploadAndAsk(file: File, question: string) {
  // 1. Upload document
  const uploadResult = await uploadDocument(file);
  const docId = uploadResult.document_id;
  console.log(`Uploaded: ${docId}, ${uploadResult.chunks_indexed} chunks`);
  
  // 2. Ask question scoped to this document
  const answer = await askQuestion(question, docId);
  console.log('Answer:', answer.answer);
  console.log('Sources:', answer.sources);
  
  return { uploadResult, answer };
}
```

### Document Selector Component

```typescript
import { useState, useEffect } from 'react';

function DocumentSelector({ onSelect }: { onSelect: (docId: string) => void }) {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [selected, setSelected] = useState<string>('');
  
  useEffect(() => {
    listDocuments().then(res => setDocuments(res.documents));
  }, []);
  
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const docId = e.target.value;
    setSelected(docId);
    onSelect(docId);
  };
  
  return (
    <select value={selected} onChange={handleChange}>
      <option value="">All documents</option>
      {documents.map(doc => (
        <option key={doc.document_id} value={doc.document_id}>
          {doc.filename}
        </option>
      ))}
    </select>
  );
}
```

### Error Handling

```typescript
async function safeAsk(question: string, documentId?: string) {
  try {
    return await askQuestion(question, documentId);
  } catch (err) {
    if (err instanceof Response) {
      const body = await err.json();
      if (err.status === 429) {
        alert('Rate limit exceeded. Please wait a moment.');
      } else if (err.status === 401) {
        alert('Invalid API key');
      } else {
        alert(`Error: ${body.error || err.statusText}`);
      }
    }
    throw err;
  }
}
```

---

## Rate Limiting

If rate limits are configured in backend `.env`:

```
RATE_LIMIT_ASK_PER_MIN=60
RATE_LIMIT_UPLOAD_PER_MIN=10
RATE_LIMIT_DELETE_PER_MIN=30
```

**429 Response:**
```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT",
  "limit_per_min": 60,
  "retry_in_seconds": 42
}
```

**Handling:**
```typescript
if (response.status === 429) {
  const body = await response.json();
  const retryAfter = body.retry_in_seconds || 60;
  alert(`Too many requests. Try again in ${retryAfter} seconds.`);
}
```

---

## Recommended Workflow: Active Document Pattern

The **active document pattern** simplifies your frontend by eliminating the need to pass `document_id` on every `/ask` request.

### How It Works

1. **Upload** a document → get `document_id`
2. **Set as active** via `POST /active-document`
3. **Ask questions** without specifying `document_id` → automatically scoped to active document
4. **Switch documents** by setting a new active document
5. **Clear active** to search across all documents

### Complete Example

```typescript
import { useState } from 'react';

function ChatInterface() {
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{q: string, a: string}>>([]);

  // 1. Upload and set active
  const handleFileUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadRes = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: { 'X-API-Key': API_KEY },
      body: formData
    });
    const { document_id, filename } = await uploadRes.json();
    
    // Set as active document
    await fetch(`${API_BASE_URL}/active-document`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id })
    });
    
    setActiveDocId(document_id);
    alert(`${filename} uploaded and set as active!`);
  };

  // 2. Ask questions (no document_id needed!)
  const handleAsk = async (question: string) => {
    const res = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
      },
      body: JSON.stringify({ question })  // No document_id!
    });
    const { answer } = await res.json();
    setMessages([...messages, { q: question, a: answer }]);
  };

  // 3. Switch active document
  const handleDocumentSwitch = async (documentId: string) => {
    await fetch(`${API_BASE_URL}/active-document`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: documentId })
    });
    setActiveDocId(documentId);
    setMessages([]);  // Clear chat history
  };

  // 4. Clear active (search all documents)
  const handleClearActive = async () => {
    await fetch(`${API_BASE_URL}/active-document`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: null })
    });
    setActiveDocId(null);
  };

  return (
    <div>
      <input type="file" onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])} />
      {activeDocId && <p>Active: {activeDocId} <button onClick={handleClearActive}>Clear</button></p>}
      
      {messages.map((m, i) => (
        <div key={i}>
          <p><strong>Q:</strong> {m.q}</p>
          <p><strong>A:</strong> {m.a}</p>
        </div>
      ))}
      
      <input 
        placeholder="Ask a question..." 
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            handleAsk(e.currentTarget.value);
            e.currentTarget.value = '';
          }
        }}
      />
    </div>
  );
}
```

### Benefits

✅ **Simpler Code**: No need to track and pass `document_id` on every query  
✅ **Better UX**: Users see which document is "in context" at the top of the chat  
✅ **Cleaner State**: Active document is managed server-side (no prop drilling)  
✅ **Flexible**: Can still override with explicit `document_id` when needed  

### When to Use

- **Single-document chat**: User uploads one document and asks questions about it
- **Document-switching**: User has multiple documents and switches between them
- **Focused analysis**: User wants all queries to stay scoped to one document

### When NOT to Use

- **Multi-document search**: User wants to search across all documents at once (pass `document_id: null` or omit active document)
- **Comparison queries**: "Compare document A and B" (requires custom logic)

---

## Quick Testing (Browser Console)

```javascript
// Test health
fetch('http://127.0.0.1:5000/health').then(r => r.json()).then(console.log);

// Test ask (all documents)
fetch('http://127.0.0.1:5000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-API-Key': 'your_key' },
  body: JSON.stringify({ question: 'Summarize the main points' })
}).then(r => r.json()).then(console.log);

// Test documents list
fetch('http://127.0.0.1:5000/documents').then(r => r.json()).then(console.log);
```

---

## CORS Note

Backend is configured with `FRONTEND_ORIGIN` in `.env`. For local dev:

```ini
FRONTEND_ORIGIN=http://localhost:5173
```

For production, set to your frontend domain. If you see CORS errors, verify this setting.

---

## Next Steps

1. **Integrate upload**: Add file input and call `uploadDocument()`.
2. **Implement active document pattern** (recommended): Set active document after upload, ask questions without `document_id`.
3. **Add document selector**: Use `DocumentSelector` component to switch between documents.
4. **Implement ask**: Call `askQuestion()` - automatically uses active document.
5. **Display sources**: Render `sources` array with citations and page numbers.
6. **Handle errors**: Show user-friendly messages for 400/401/429.
7. **Optional warmup**: Call `/rag/warmup` on app load to reduce first-query latency.

**See also**: `ESSENTIAL_ENDPOINTS.md` for prioritized endpoint list (MUST-HAVE vs RECOMMENDED vs OPTIONAL).

Let me know if you need help with any specific React component!
