"""
Vector Store Module

Handles embedding generation, vector storage using FAISS,
and similarity search operations.
"""

import os
import json
import pickle
from typing import List, Dict, Any, Optional, Tuple
import logging

import numpy as np
import faiss

from .config import RAGConfig


logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for document embeddings."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.model = None
        self.index = None
        self.document_map = {}  # Maps vector index to document info
        self._ensure_directory()
        self._load_or_create_index()
    
    def _ensure_directory(self) -> None:
        """Create vector store directory if it doesn't exist."""
        os.makedirs(self.config.vector_db_path, exist_ok=True)
    
    def _load_embedding_model(self) -> None:
        """Load the sentence transformer model lazily to reduce startup memory."""
        if self.model is None:
            try:
                # Lazy import to avoid heavy torch load at module import time
                from sentence_transformers import SentenceTransformer  # type: ignore
                logger.info(f"Loading embedding model: {self.config.embedding_model}")
                self.model = SentenceTransformer(
                    self.config.embedding_model,
                    device=self.config.device
                )
                logger.info("Embedding model loaded successfully")
            except (OSError, MemoryError) as e:
                # Common on Windows when pagefile is too small (WinError 1455)
                msg = (
                    "Failed to load embedding model. This often happens on Windows when the paging file is too small. "
                    "Increase virtual memory (Control Panel > System > Advanced system settings > Performance Settings > Advanced > Virtual memory) "
                    "or use a smaller embedding backend. Original error: " + str(e)
                )
                logger.error(msg)
                raise RuntimeError(msg) from e
            except Exception as e:
                logger.error(f"Unexpected error loading embedding model: {e}")
                raise
    
    def _load_or_create_index(self) -> None:
        """Load existing FAISS index or create a new one."""
        index_path = os.path.join(self.config.vector_db_path, "faiss_index.bin")
        mapping_path = os.path.join(self.config.vector_db_path, "document_mapping.pkl")
        
        if os.path.exists(index_path) and os.path.exists(mapping_path):
            try:
                # Load existing index
                self.index = faiss.read_index(index_path)
                
                # Load document mapping
                with open(mapping_path, 'rb') as f:
                    self.document_map = pickle.load(f)
                
                logger.info(f"Loaded existing index with {self.index.ntotal} vectors")
                return
            except Exception as e:
                logger.warning(f"Failed to load existing index: {str(e)}")
        
        # Create new index
        self.index = faiss.IndexFlatIP(self.config.embedding_dimension)  # Cosine similarity
        self.document_map = {}
        logger.info("Created new FAISS index")
    
    def _save_index(self) -> None:
        """Save FAISS index and document mapping to disk."""
        try:
            index_path = os.path.join(self.config.vector_db_path, "faiss_index.bin")
            mapping_path = os.path.join(self.config.vector_db_path, "document_mapping.pkl")
            
            # Save FAISS index
            faiss.write_index(self.index, index_path)
            
            # Save document mapping
            with open(mapping_path, 'wb') as f:
                pickle.dump(self.document_map, f)
            
            logger.info("Successfully saved vector index")
        except Exception as e:
            logger.error(f"Failed to save index: {str(e)}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if not texts:
            return np.array([])
        
        self._load_embedding_model()
        
        try:
            # Generate embeddings in batches
            embeddings = []
            batch_size = self.config.batch_size
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # For cosine similarity
                )
                embeddings.append(batch_embeddings)
            
            # Concatenate all embeddings
            all_embeddings = np.vstack(embeddings) if embeddings else np.array([])
            logger.info(f"Generated {len(all_embeddings)} embeddings")
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise
    
    def add_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of chunk dictionaries with keys:
                - text: The text content
                - document_id: Source document ID
                - chunk_id: Unique chunk identifier
                - metadata: Additional metadata (page, etc.)
        """
        if not chunks:
            logger.warning("No chunks provided to add_documents")
            return
        
        try:
            # Extract texts for embedding
            texts = [chunk['text'] for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            
            if len(embeddings) == 0:
                logger.warning("No embeddings generated")
                return
            
            # Add to FAISS index
            start_index = self.index.ntotal
            self.index.add(embeddings.astype(np.float32))
            
            # Update document mapping
            for i, chunk in enumerate(chunks):
                vector_index = start_index + i
                self.document_map[vector_index] = {
                    'document_id': chunk['document_id'],
                    'chunk_id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'metadata': chunk.get('metadata', {})
                }
            
            # Save to disk
            self._save_index()
            
            logger.info(f"Added {len(chunks)} chunks to vector store. Total vectors: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {str(e)}")
            raise
    
    def search(self, query: str, k: Optional[int] = None, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            k: Number of results to return (defaults to config.top_k_results)
            document_id: Optional document ID to limit search scope
        
        Returns:
            List of search results with similarity scores
        """
        if k is None:
            k = self.config.top_k_results
        
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])
            
            if len(query_embedding) == 0:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Search FAISS index
            scores, indices = self.index.search(
                query_embedding.astype(np.float32), 
                min(k, self.index.ntotal)
            )
            
            # Format results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for invalid indices
                    continue
                
                # Apply similarity threshold
                if score < self.config.similarity_threshold:
                    continue
                
                # Get document info
                doc_info = self.document_map.get(idx, {})
                
                # Filter by document_id if specified
                if document_id and doc_info.get('document_id') != document_id:
                    continue
                
                result = {
                    'score': float(score),
                    'document_id': doc_info.get('document_id', 'unknown'),
                    'chunk_id': doc_info.get('chunk_id', 'unknown'),
                    'text': doc_info.get('text', ''),
                    'metadata': doc_info.get('metadata', {})
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} relevant chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.config.embedding_dimension,
            'model_name': self.config.embedding_model,
            'similarity_threshold': self.config.similarity_threshold,
            'unique_documents': len(set(
                info.get('document_id', '') 
                for info in self.document_map.values()
            )) if self.document_map else 0
        }
    
    def remove_document(self, document_id: str) -> int:
        """
        Remove all vectors for a specific document.
        Note: FAISS doesn't support efficient deletion, so this rebuilds the index.
        """
        if not self.document_map:
            return 0
        
        # Find indices to keep (not belonging to the document)
        indices_to_keep = []
        for idx, info in self.document_map.items():
            if info.get('document_id') != document_id:
                indices_to_keep.append(idx)
        
        if len(indices_to_keep) == len(self.document_map):
            logger.info(f"Document {document_id} not found in vector store")
            return 0
        
        removed_count = len(self.document_map) - len(indices_to_keep)
        
        if len(indices_to_keep) == 0:
            # Remove all vectors
            self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
            self.document_map = {}
        else:
            # Rebuild index with remaining vectors
            logger.info(f"Rebuilding index after removing {removed_count} vectors")
            
            # Extract vectors and documents to keep
            vectors_to_keep = []
            new_document_map = {}
            
            for new_idx, old_idx in enumerate(indices_to_keep):
                # Get vector from old index
                vector = self.index.reconstruct(old_idx)
                vectors_to_keep.append(vector)
                
                # Update mapping with new index
                new_document_map[new_idx] = self.document_map[old_idx]
            
            # Create new index
            self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
            if vectors_to_keep:
                vectors_array = np.vstack(vectors_to_keep)
                self.index.add(vectors_array.astype(np.float32))
            
            self.document_map = new_document_map
        
        # Save updated index
        self._save_index()
        
        logger.info(f"Removed {removed_count} vectors for document {document_id}")
        return removed_count
    
    def clear(self) -> None:
        """Clear all vectors from the store."""
        self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
        self.document_map = {}
        self._save_index()
        logger.info("Cleared all vectors from store")
