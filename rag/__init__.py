"""
RAG (Retrieval-Augmented Generation) Pipeline

This package contains all components for document processing,
embedding generation, vector search, and AI response generation.
"""

__version__ = "0.1.0"

# Import main components for easy access
from .config import RAGConfig
from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .retrieval import RetrieverEngine
from .response_generator import ResponseGenerator

__all__ = [
    "RAGConfig",
    "DocumentProcessor", 
    "VectorStore",
    "RetrieverEngine",
    "ResponseGenerator"
]
