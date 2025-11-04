"""
Retrieval Engine Module

Handles query processing and context retrieval from the vector store.
"""

from typing import List, Dict, Any, Optional
import logging
import re

from .config import RAGConfig
from .vector_store import VectorStore


logger = logging.getLogger(__name__)


class RetrieverEngine:
    """Main retrieval engine for RAG pipeline."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.vector_store = VectorStore(config)
    
    @staticmethod
    def _is_low_quality_chunk(text: str) -> bool:
        """
        Detect low-quality chunks like table of contents, headers, or metadata.
        
        Args:
            text: Chunk text to evaluate
            
        Returns:
            True if chunk appears to be low quality
        """
        if not text or len(text.strip()) < 20:
            return True
        
        lines = text.strip().split('\n')
        
        # Check if it looks like a table of contents
        toc_indicators = 0
        for line in lines:
            line_stripped = line.strip()
            # TOC lines often have: dots, page numbers, section numbers
            if re.search(r'\.{3,}', line_stripped):  # Multiple dots (.....)
                toc_indicators += 1
            if re.search(r'^[\d.]+\s+[A-Z].*\s+\d+$', line_stripped):  # "1.1 Title 3"
                toc_indicators += 1
            if re.match(r'^\d+\.\d+\s+.*Code\s*\.+\s*\d+$', line_stripped):  # "1.1 Python Code . . . 3"
                toc_indicators += 1
        
        # If more than 50% of lines look like TOC, mark as low quality
        if len(lines) > 0 and toc_indicators / len(lines) > 0.5:
            logger.debug(f"Filtered TOC-like chunk: {text[:100]}...")
            return True
        
        # Check if it's just section headers or minimal content
        if len(lines) <= 3 and all(len(line.strip()) < 50 for line in lines):
            # Short chunks with very brief lines are likely headers/metadata
            return True
        
        return False
    
    def retrieve(self, query: str, k: Optional[int] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User query
            k: Number of results to retrieve
            document_id: Optional document ID to limit retrieval scope
            
        Returns:
            Dictionary containing context and metadata
        """
        try:
            # Search vector store
            search_results = self.vector_store.search(query, k, document_id=document_id)
            
            if not search_results:
                return {
                    'context': "",
                    'sources': [],
                    'retrieval_stats': {
                        'query': query,
                        'results_found': 0,
                        'avg_score': 0.0
                    }
                }
            
            # Filter out low-quality chunks (TOC, headers, metadata)
            filtered_results = []
            filtered_count = 0
            for result in search_results:
                if not self._is_low_quality_chunk(result['text']):
                    filtered_results.append(result)
                else:
                    filtered_count += 1
            
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} low-quality chunks from {len(search_results)} results")
            
            # If we filtered everything, use original results (better than nothing)
            if not filtered_results:
                logger.warning("All chunks were filtered as low-quality, using original results")
                filtered_results = search_results
            
            # Build context and sources
            context_parts = []
            sources = []
            total_score = 0
            
            for result in filtered_results:
                # Add to context
                context_parts.append(result['text'])
                
                # Add to sources
                sources.append({
                    'document_id': result['document_id'],
                    'chunk_id': result['chunk_id'],
                    'score': result['score'],
                    'page': result['metadata'].get('page', 1),
                    'snippet': result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
                })
                
                total_score += result['score']
            
            # Combine context
            combined_context = "\n\n---\n\n".join(context_parts)
            
            # Truncate if too long
            if len(combined_context) > self.config.max_context_length:
                combined_context = combined_context[:self.config.max_context_length] + "..."
                logger.info(f"Context truncated to {self.config.max_context_length} characters")
            
            return {
                'context': combined_context,
                'sources': sources,
                'retrieval_stats': {
                    'query': query,
                    'results_found': len(filtered_results),
                    'total_retrieved': len(search_results),
                    'filtered_out': len(search_results) - len(filtered_results),
                    'avg_score': total_score / len(filtered_results) if filtered_results else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Retrieval failed: {str(e)}")
            return {
                'context': "",
                'sources': [],
                'retrieval_stats': {
                    'query': query,
                    'results_found': 0,
                    'avg_score': 0.0,
                    'error': str(e)
                }
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval engine statistics."""
        return {
            'vector_store_stats': self.vector_store.get_stats(),
            'config': {
                'top_k_results': self.config.top_k_results,
                'similarity_threshold': self.config.similarity_threshold,
                'max_context_length': self.config.max_context_length
            }
        }
