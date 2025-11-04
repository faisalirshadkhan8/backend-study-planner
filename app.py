from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import logging
import json
import time
import uuid
from dotenv import load_dotenv
import random
from typing import Any, Optional, Tuple
from werkzeug.utils import secure_filename
import re
from copy import deepcopy

# RAG components (import lazily inside routes where heavy)
try:
    from rag.config import RAGConfig  # lightweight
    from rag.vector_store import VectorStore  # initializes FAISS, lazy-loads model
except Exception as _e:
    # Defer errors until endpoints are called; keep server boot light
    RAGConfig = None  # type: ignore
    VectorStore = None  # type: ignore

# Load environment variables from .env file
load_dotenv()

APP_VERSION = "0.1.0"


def generate_response(question):
    """Generate a smart response based on the question."""
    question_lower = question.lower().strip()
    
    # Greeting responses
    if any(word in question_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        responses = [
            "Hello! I'm your AI assistant. How can I help you today?",
            "Hi there! What would you like to know?",
            "Hey! I'm here to help. What's on your mind?",
            "Greetings! Feel free to ask me anything.",
            "Hello! I'm ready to assist you with your questions."
        ]
        return random.choice(responses)
    
    # How are you responses
    elif any(phrase in question_lower for phrase in ['how are you', 'how do you do', 'how\'s it going']):
        responses = [
            "I'm doing great! Thanks for asking. How can I assist you?",
            "I'm functioning perfectly and ready to help!",
            "All systems operational! What can I do for you?",
            "I'm excellent, thank you! How may I help you today?"
        ]
        return random.choice(responses)
    
    # What can you do responses
    elif any(phrase in question_lower for phrase in ['what can you do', 'what do you do', 'help me', 'capabilities']):
        responses = [
            "I'm a RAG-powered chatbot! I can answer questions, have conversations, and help with various topics. What would you like to explore?",
            "I can help you with questions, provide information, and have meaningful conversations. Try asking me about any topic!",
            "I'm here to assist with answering questions and providing helpful information. What would you like to know?",
            "I can engage in conversations, answer questions, and provide assistance on various topics. How can I help you today?"
        ]
        return random.choice(responses)
    
    # Goodbye responses
    elif any(word in question_lower for word in ['bye', 'goodbye', 'see you', 'farewell', 'exit']):
        responses = [
            "Goodbye! It was nice chatting with you. Come back anytime!",
            "See you later! Feel free to return whenever you have questions.",
            "Farewell! Thanks for the conversation. Have a great day!",
            "Bye! Hope I was helpful. Until next time!"
        ]
        return random.choice(responses)
    
    # Thank you responses
    elif any(phrase in question_lower for phrase in ['thank you', 'thanks', 'appreciate', 'grateful']):
        responses = [
            "You're very welcome! Happy to help anytime.",
            "My pleasure! Let me know if you need anything else.",
            "Glad I could help! Feel free to ask more questions.",
            "You're welcome! I'm here whenever you need assistance."
        ]
        return random.choice(responses)
    
    # Name/identity questions
    elif any(phrase in question_lower for phrase in ['what is your name', 'who are you', 'your name']):
        responses = [
            "I'm your RAG-powered AI assistant! You can call me whatever you'd like.",
            "I'm an AI chatbot designed to help answer your questions. What should I call you?",
            "I'm your helpful AI assistant. I don't have a specific name yet - got any suggestions?",
            "I'm an AI assistant here to help you. What would you like to know?"
        ]
        return random.choice(responses)
    
    # Test responses
    elif any(word in question_lower for word in ['test', 'testing', 'check']):
        responses = [
            "Test successful! I'm working perfectly and ready to chat.",
            "Testing complete! Everything looks good. What's your real question?",
            "System check passed! I'm functioning normally. How can I help?",
            "Test confirmed! I'm online and ready to assist you."
        ]
        return random.choice(responses)
    
    # Default response for unrecognized questions
    else:
        responses = [
            f"That's an interesting question about '{question}'. I'm still learning! Can you tell me more?",
            f"I see you're asking about '{question}'. While I'm still developing my knowledge base, I'd love to learn more about this topic from you!",
            f"'{question}' is a great question! I'm currently a basic chatbot, but I'm being enhanced with RAG capabilities. What specifically would you like to know?",
            f"Thanks for asking about '{question}'! I'm in development mode right now. Can you provide more context so I can better assist you?",
            f"Interesting topic: '{question}'. I'm learning every day! What aspect interests you most?"
        ]
        return random.choice(responses)

app = Flask(__name__)

# Configure logging (basic for now; can be expanded with handlers/formatters)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger("backend")


@app.before_request
def _start_timer_and_request_id():
    g._start_time = time.time()
    g.request_id = str(uuid.uuid4())


@app.after_request
def _log_request(response):
    try:
        duration = int((time.time() - getattr(g, '_start_time', time.time())) * 1000)
        record = {
            "ts": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()) + f".{int((time.time()%1)*1000):03d}Z",
            "level": "INFO",
            "request_id": getattr(g, 'request_id', None),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "latency_ms": duration,
            "remote_addr": request.remote_addr,
            "content_length": response.calculate_content_length(),
            "user_agent": request.headers.get('User-Agent', '')[:200],
            "message": "request"
        }
        logger.info(json.dumps(record))
    except Exception:
        logger.exception("failed to log request")
    return response

"""Security & Rate Limiting using flask-limiter."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def _check_api_key_only() -> Optional[Tuple[Any, int]]:
    required_key = os.getenv("API_KEY") or ""
    if not required_key:
        return None
    provided = request.headers.get("X-API-Key", "")
    if provided != required_key:
        return jsonify({"error": "Unauthorized", "code": "API_KEY_INVALID"}), 401
    return None

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],  # all explicit
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)

def _dynamic_limit(env_name: str, default: int) -> str:
    try:
        v = int(os.getenv(env_name, str(default)) or default)
    except ValueError:
        v = default
    if v <= 0:
        return "0 per minute"  # effectively no limit
    return f"{v} per minute"

ASK_LIMIT = _dynamic_limit("RATE_LIMIT_ASK_PER_MIN", 60)
UPLOAD_LIMIT = _dynamic_limit("RATE_LIMIT_UPLOAD_PER_MIN", 10)
DELETE_LIMIT = _dynamic_limit("RATE_LIMIT_DELETE_PER_MIN", 30)

# Active document state (in-memory; per-session tracking would need Redis/DB)
_active_document_store = {}  # Maps session/IP to active document_id

# Restrict CORS origins in production by replacing '*' with your frontend URL
CORS(app, resources={r"/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})


@app.route("/health", methods=["GET"])
def health():
    """Liveness & readiness probe."""
    return jsonify({
        "status": "ok",
        "version": APP_VERSION
    }), 200


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "basic-rag-chatbot-backend",
        "version": APP_VERSION,
        "endpoints": [
            "/health",
            "/ask",
            "/active-document",
            "/rag/warmup",
            "/upload",
            "/documents",
            "/documents/<document_id>",
            "/rag/stats",
        ],
        "message": "Backend operational"
    }), 200

@app.route("/active-document", methods=["POST"])
def set_active_document():
    """
    Set the active document for the current session.
    This document will be automatically used for /ask queries when no explicit document_id is provided.
    
    Request JSON:
        {
            "document_id": "doc_abc123" | null  // null to clear active document
        }
    
    Returns:
        200: {"message": "Active document set", "document_id": "doc_abc123"}
        200: {"message": "Active document cleared"} (when document_id is null)
        415: Content-Type must be application/json
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    
    data = request.get_json(silent=True) or {}
    document_id = data.get("document_id")
    session_key = request.remote_addr or "default"
    
    if document_id is None:
        # Clear active document
        _active_document_store.pop(session_key, None)
        return jsonify({"message": "Active document cleared"}), 200
    else:
        # Set active document
        _active_document_store[session_key] = document_id
        return jsonify({
            "message": "Active document set",
            "document_id": document_id
        }), 200

@app.route("/active-document", methods=["GET"])
def get_active_document():
    """
    Get the currently active document for the current session.
    
    Returns:
        200: {"document_id": "doc_abc123" | null}
    """
    session_key = request.remote_addr or "default"
    document_id = _active_document_store.get(session_key)
    return jsonify({"document_id": document_id}), 200

@app.route("/ask", methods=["POST"])
@limiter.limit(ASK_LIMIT)
def ask():
    """Answer a user question.

    Expected JSON body:
    {
        "question": "<string>"
    }
    """
    # API key enforcement (if configured)
    unauthorized = _check_api_key_only()
    if unauthorized:
        return unauthorized

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415


    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    document_id = data.get("document_id")
    
    # Auto-resolve active document if not explicitly provided
    if not document_id:
        session_key = request.remote_addr or "default"
        document_id = _active_document_store.get(session_key)

    if not question:
        return jsonify({"error": "'question' is required and cannot be empty"}), 400

    # If vector store has data, use RAG pipeline; otherwise use smart stub
    try:
        from rag.config import RAGConfig
        from rag.retrieval import RetrieverEngine
        from rag.response_generator import ResponseGenerator
    except Exception:
        RAGConfig = None  # type: ignore
        RetrieverEngine = None  # type: ignore
        ResponseGenerator = None  # type: ignore

    if RAGConfig and RetrieverEngine and ResponseGenerator:
        cfg = RAGConfig.from_env()
        retriever = RetrieverEngine(cfg)
        stats = retriever.get_stats()
        total_vectors = stats.get("vector_store_stats", {}).get("total_vectors", 0)

        if total_vectors and total_vectors > 0:
            retrieval = retriever.retrieve(question, None, document_id=document_id)
            context = retrieval.get("context", "")
            sources = retrieval.get("sources", [])

            # If nothing found, try a second pass with looser settings
            if (not context or not sources):
                cfg2 = deepcopy(cfg)
                try:
                    cfg2.similarity_threshold = 0.3
                    cfg2.top_k_results = max(8, getattr(cfg, "top_k_results", 5))
                except Exception:
                    pass
                retriever2 = RetrieverEngine(cfg2)
                retrieval2 = retriever2.retrieve(question, None, document_id=document_id)
                if retrieval2.get("sources"):
                    context = retrieval2.get("context", context)
                    sources = retrieval2.get("sources", sources)
            responder = ResponseGenerator(cfg)
            resp = responder.generate_response(question, context, sources)
            # Align response shape
            answer_text = resp.get("answer", "")
            resp_sources = resp.get("sources", [])

            # Contact-info fallback: if no sources/context and question asks for email/phone
            ql = question.lower()
            if (not answer_text or not resp_sources) and ("email" in ql or "phone" in ql or "contact" in ql):
                emails = set()
                phones = set()
                src_files = []
                try:
                    # Scan processed text files for contact info
                    processed_dir = getattr(cfg, "processed_folder", None) or os.path.join("documents", "processed")
                    if os.path.isdir(processed_dir):
                        for fname in os.listdir(processed_dir):
                            if fname.endswith(".txt"):
                                fpath = os.path.join(processed_dir, fname)
                                try:
                                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                        txt = f.read()
                                    # Simple regex for emails and phone numbers
                                    emails.update(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", txt))
                                    phones.update(re.findall(r"(?:\\+?\\d{1,3}[ -]?)?(?:\\(\\d{2,4}\\)[ -]?|\\d{2,4}[ -])?\\d{3,4}[ -]?\\d{3,4}", txt))
                                    src_files.append(fpath)
                                except Exception:
                                    continue
                    if emails or phones:
                        lines = []
                        if emails:
                            lines.append("Found email(s): " + ", ".join(sorted(emails)))
                        if phones:
                            lines.append("Found phone(s): " + ", ".join(sorted(phones)))
                        contact_answer = "\n".join(lines)
                        # Build sources list from file names
                        fallback_sources = [{"type": "file", "path": p} for p in src_files]
                        return jsonify({
                            "answer": contact_answer,
                            "sources": fallback_sources,
                            "meta": {
                                "model": "regex-fallback",
                                "has_sources": True,
                                "context_length": 0,
                                "tokens_used": 0,
                                "generation_time_ms": 0
                            }
                        }), 200
                except Exception:
                    pass

            # Generic keyword fallback: scan processed text for lines matching query terms
            if (not answer_text or not resp_sources) and total_vectors:
                try:
                    processed_dir = getattr(cfg, "processed_folder", None) or os.path.join("documents", "processed")
                    if os.path.isdir(processed_dir):
                        # Basic keyword extraction from question
                        stop = set(["the","is","are","a","an","and","or","of","to","in","for","with","what","which","who","does","do","list","show","tell","about","email","phone","contact"])
                        terms = [t.lower() for t in re.findall(r"[A-Za-z0-9#.+-]+", ql) if t.lower() not in stop]
                        matches = []
                        # Only scan specified document if document_id is present
                        if document_id:
                            fpaths = [os.path.join(processed_dir, f"{document_id}.txt")]
                        else:
                            fpaths = [os.path.join(processed_dir, fname) for fname in os.listdir(processed_dir) if fname.endswith(".txt")]
                        for fpath in fpaths:
                            if not os.path.isfile(fpath):
                                continue
                            try:
                                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                    for i, line in enumerate(f):
                                        l = line.strip()
                                        if not l:
                                            continue
                                        score = sum(1 for term in terms if term and term in l.lower())
                                        if score:
                                            matches.append((score, fpath, i+1, l))
                            except Exception:
                                continue
                        if matches:
                            # Take top by score
                            matches.sort(key=lambda x: (-x[0], x[1], x[2]))
                            top = matches[:8]
                            snippets = [f"{os.path.basename(p)}: {txt}" for _, p, _, txt in top]
                            answer_kw = "\n".join(snippets)
                            srcs = []
                            seen = set()
                            for _, p, _, _ in top:
                                if p not in seen:
                                    seen.add(p)
                                    srcs.append({"type": "file", "path": p})
                            return jsonify({
                                "answer": answer_kw,
                                "sources": srcs,
                                "meta": {"model": "keyword-fallback", "has_sources": True, "context_length": 0, "tokens_used": 0, "generation_time_ms": 0}
                            }), 200
                except Exception:
                    pass

            return jsonify({
                "answer": answer_text,
                "sources": resp_sources,
                "meta": resp.get("meta", {})
            }), 200

    # Fallback smart stub
    answer_text = generate_response(question)
    return jsonify({
        "answer": answer_text,
        "sources": [],
        "meta": {"model": "stub", "latency_ms": 0, "source_count": 0}
    }), 200


@app.route("/rag/warmup", methods=["GET"])
def rag_warmup():
    """Warm up the RAG pipeline by loading the embedding model once.

    Does not modify any state; just tests that embeddings can be generated.
    """
    try:
        # Lazy import to avoid torch import on app startup
        from rag.config import RAGConfig
        from rag.vector_store import VectorStore

        cfg = RAGConfig.from_env()
        cfg.validate()
        vs = VectorStore(cfg)
        # Tiny smoke test: generate one embedding
        _ = vs.generate_embeddings(["warmup test"])  # noqa: F841

        return jsonify({
            "status": "ok",
            "device": cfg.device,
            "embedding_model": cfg.embedding_model,
            "vector_store": vs.get_stats(),
        }), 200
    except Exception as e:
        # Do not crash server; return actionable error
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/upload", methods=["POST"])
@limiter.limit(UPLOAD_LIMIT)
def upload_document():
    """Upload a document, extract text, chunk, and index into vector store."""
    try:
        unauthorized = _check_api_key_only()
        if unauthorized:
            return unauthorized
        if "file" not in request.files:
            return jsonify({"error": "No file part in request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        from rag.config import RAGConfig
        from rag.document_processor import DocumentProcessor
        from rag.chunking import TextChunker
        from rag.vector_store import VectorStore

        cfg = RAGConfig.from_env()
        processor = DocumentProcessor(cfg)
        ok, message, meta = processor.upload_document(file)
        if not ok or not meta:
            return jsonify({"error": message}), 400

        # Load processed text
        doc_id = meta.document_id
        processed_path = os.path.join(cfg.processed_folder, f"{doc_id}.txt")
        with open(processed_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        # Chunk and index
        chunker = TextChunker(cfg)
        chunks = chunker.chunk_text(text, doc_id)
        vs = VectorStore(cfg)
        vs.add_documents(chunks)

        # Update document metadata chunk count (rewrite metadata json)
        meta_path = os.path.join(cfg.metadata_folder, f"{doc_id}.json")
        try:
            import json
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_json = json.load(f)
            meta_json["chunk_count"] = len(chunks)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_json, f, indent=2)
        except Exception:
            pass

        return jsonify({
            "message": message,
            "document_id": doc_id,
            "chunks_indexed": len(chunks),
            "vector_store": vs.get_stats(),
        }), 201
    except NotImplementedError as nie:
        return jsonify({"error": str(nie)}), 400
    except Exception as e:
        logger.exception("Upload failed")
        return jsonify({"error": str(e)}), 500


@app.route("/documents", methods=["GET"])
def list_documents():
    """List all processed documents with basic metadata."""
    try:
        from rag.config import RAGConfig
        from rag.document_processor import DocumentProcessor

        cfg = RAGConfig.from_env()
        processor = DocumentProcessor(cfg)
        docs = processor.list_documents()
        # Serialize
        result = []
        for d in docs:
            result.append({
                "document_id": d.document_id,
                "filename": d.filename,
                "file_size": d.file_size,
                "file_type": d.file_type,
                "upload_time": d.upload_time.isoformat(),
                "processed_time": d.processed_time.isoformat() if d.processed_time else None,
                "text_length": d.text_length,
                "chunk_count": d.chunk_count,
                "status": d.status,
            })
        return jsonify({"documents": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/documents/<document_id>", methods=["DELETE"])
@limiter.limit(DELETE_LIMIT)
def delete_document(document_id: str):
    """Delete a document and its vectors from the store."""
    try:
        unauthorized = _check_api_key_only()
        if unauthorized:
            return unauthorized
        from rag.config import RAGConfig
        from rag.document_processor import DocumentProcessor
        from rag.vector_store import VectorStore

        cfg = RAGConfig.from_env()
        vs = VectorStore(cfg)
        removed = vs.remove_document(document_id)

        processor = DocumentProcessor(cfg)
        ok, msg = processor.delete_document(document_id)
        status = 200 if ok else 404
        return jsonify({
            "vectors_removed": removed,
            "message": msg,
            "vector_store": vs.get_stats(),
        }), status
    except Exception as e:
        logger.exception("Delete failed")
        return jsonify({"error": str(e)}), 500


@app.route("/documents/<document_id>/content", methods=["GET"])
def get_document_content(document_id: str):
    """Get document content for preview or citation (returns first 5000 chars by default)."""
    try:
        from rag.config import RAGConfig
        cfg = RAGConfig.from_env()
        processed_dir = getattr(cfg, "processed_folder", None) or os.path.join("documents", "processed")
        processed_path = os.path.join(processed_dir, f"{document_id}.txt")
        
        if not os.path.exists(processed_path):
            return jsonify({"error": "Document not found"}), 404
        
        # Get optional query param for max length
        max_length = request.args.get('max_length', 5000, type=int)
        
        with open(processed_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_length)
        
        metadata_dir = getattr(cfg, "metadata_folder", None) or os.path.join("documents", "metadata")
        metadata_path = os.path.join(metadata_dir, f"{document_id}.json")
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        return jsonify({
            "document_id": document_id,
            "content": content,
            "full_length": len(content),
            "truncated": len(content) == max_length,
            "metadata": metadata
        }), 200
    except Exception as e:
        logger.exception("Get document content failed")
        return jsonify({"error": str(e)}), 500


@app.route("/rag/stats", methods=["GET"])
def rag_stats():
    """Return RAG and vector store statistics."""
    try:
        from rag.config import RAGConfig
        from rag.retrieval import RetrieverEngine

        cfg = RAGConfig.from_env()
        engine = RetrieverEngine(cfg)
        stats = engine.get_stats()
        return jsonify({"status": "ok", **stats}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    logger.exception("Unhandled server error")
    return jsonify({"error": "Internal server error"}), 500


    

if __name__ == "__main__":
    # Avoid enabling debug/reloader on low-memory Windows environments, as it can
    # spawn extra processes that fail when pagefile is small. Control with env DEBUG.
    debug_enabled = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(port=5000, debug=debug_enabled, use_reloader=False)
