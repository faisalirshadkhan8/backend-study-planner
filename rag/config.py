"""
RAG Configuration Management

Centralized configuration for all RAG pipeline components.
Loads from environment variables with sensible defaults.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class RAGConfig:
    """Configuration class for RAG pipeline settings."""
    
    # Document Processing
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: tuple = ('.pdf', '.txt', '.docx')
    upload_folder: str = './documents/raw'
    processed_folder: str = './documents/processed'
    metadata_folder: str = './documents/metadata'
    
    # Text Chunking
    chunk_size: int = 800
    chunk_overlap: int = 150
    preserve_sentences: bool = True
    
    # Embedding Model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    device: str = "cpu"
    
    # Vector Database
    vector_db_path: str = "./vector_store"
    similarity_threshold: float = 0.7
    top_k_results: int = 5
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.1
    # LLM Provider selection
    llm_provider: str = "openai"  # options: openai, gemini
    gemini_api_key: Optional[str] = None
    
    # Performance
    batch_size: int = 32
    max_context_length: int = 4000
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Create configuration from environment variables."""
        return cls(
            # Document Processing
            max_file_size=int(os.getenv('MAX_FILE_SIZE', cls.max_file_size)),
            upload_folder=os.getenv('UPLOAD_FOLDER', cls.upload_folder),
            processed_folder=os.getenv('PROCESSED_FOLDER', cls.processed_folder),
            metadata_folder=os.getenv('METADATA_FOLDER', cls.metadata_folder),
            
            # Text Chunking
            chunk_size=int(os.getenv('CHUNK_SIZE', cls.chunk_size)),
            chunk_overlap=int(os.getenv('CHUNK_OVERLAP', cls.chunk_overlap)),
            
            # Embedding Model
            embedding_model=os.getenv('EMBEDDING_MODEL', cls.embedding_model),
            device=os.getenv('DEVICE', cls.device),
            
            # Vector Database
            vector_db_path=os.getenv('VECTOR_DB_PATH', cls.vector_db_path),
            similarity_threshold=float(os.getenv('SIMILARITY_THRESHOLD', cls.similarity_threshold)),
            top_k_results=int(os.getenv('TOP_K_RESULTS', cls.top_k_results)),
            
            # LLM Configuration
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            default_model=os.getenv('DEFAULT_MODEL', cls.default_model),
            max_tokens=int(os.getenv('MAX_TOKENS', cls.max_tokens)),
            temperature=float(os.getenv('TEMPERATURE', cls.temperature)),
            llm_provider=os.getenv('LLM_PROVIDER', cls.llm_provider),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            
            # Performance
            batch_size=int(os.getenv('BATCH_SIZE', cls.batch_size)),
            max_context_length=int(os.getenv('MAX_CONTEXT_LENGTH', cls.max_context_length)),
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.similarity_threshold < 0 or self.similarity_threshold > 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        if self.top_k_results <= 0:
            raise ValueError("top_k_results must be positive")
