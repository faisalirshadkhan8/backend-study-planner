"""
Text Chunking Module

Handles intelligent text splitting with overlap and context preservation.
"""

import re
from typing import List, Dict, Any
import logging

from .config import RAGConfig


logger = logging.getLogger(__name__)


class TextChunker:
    """Intelligent text chunking with overlap and sentence preservation."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        # Simple sentence boundary detection
        self.sentence_pattern = re.compile(r'[.!?]+\s+')
    
    def chunk_text(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text to chunk
            document_id: Source document identifier
            
        Returns:
            List of chunk dictionaries
        """
        if not text.strip():
            return []
        
        # Extract page markers if present
        pages = self._split_by_pages(text)
        
        chunks = []
        chunk_counter = 0
        
        for page_num, page_text in pages:
            page_chunks = self._chunk_page_text(page_text, document_id, page_num, chunk_counter)
            chunks.extend(page_chunks)
            chunk_counter += len(page_chunks)
        
        logger.info(f"Created {len(chunks)} chunks for document {document_id}")
        return chunks
    
    def _split_by_pages(self, text: str) -> List[tuple]:
        """Split text by page markers."""
        page_pattern = re.compile(r'\[PAGE (\d+)\]')
        pages = []
        
        parts = page_pattern.split(text)
        
        if len(parts) == 1:
            # No page markers found
            return [(1, text)]
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                page_num = int(parts[i])
                page_text = parts[i + 1].strip()
                if page_text:
                    pages.append((page_num, page_text))
        
        return pages if pages else [(1, text)]
    
    def _chunk_page_text(self, text: str, document_id: str, page_num: int, start_counter: int) -> List[Dict[str, Any]]:
        """Chunk text from a single page."""
        if not text.strip():
            return []
        
        chunks = []
        
        if self.config.preserve_sentences:
            # Split by sentences for better chunking
            sentences = self._split_sentences(text)
            chunks = self._create_sentence_chunks(sentences, document_id, page_num, start_counter)
        else:
            # Simple character-based chunking
            chunks = self._create_character_chunks(text, document_id, page_num, start_counter)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting - can be improved with spaCy/NLTK
        sentences = self.sentence_pattern.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_sentence_chunks(self, sentences: List[str], document_id: str, page_num: int, start_counter: int) -> List[Dict[str, Any]]:
        """Create chunks preserving sentence boundaries."""
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_id = start_counter
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size
            if current_length + sentence_length > self.config.chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk_dict(chunk_text, document_id, page_num, chunk_id))
                chunk_id += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_length = len(' '.join(current_chunk))
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_length += sentence_length + 1  # +1 for space
        
        # Add final chunk if not empty
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk_dict(chunk_text, document_id, page_num, chunk_id))
        
        return chunks
    
    def _create_character_chunks(self, text: str, document_id: str, page_num: int, start_counter: int) -> List[Dict[str, Any]]:
        """Create chunks based on character count."""
        chunks = []
        chunk_id = start_counter
        
        for i in range(0, len(text), self.config.chunk_size - self.config.chunk_overlap):
            end_pos = min(i + self.config.chunk_size, len(text))
            chunk_text = text[i:end_pos].strip()
            
            if chunk_text:
                chunks.append(self._create_chunk_dict(chunk_text, document_id, page_num, chunk_id))
                chunk_id += 1
        
        return chunks
    
    def _get_overlap_text(self, sentences: List[str]) -> str:
        """Get overlap text from the end of current chunk."""
        if not sentences:
            return ""
        
        # Take last few sentences that fit within overlap size
        overlap_sentences = []
        overlap_length = 0
        
        for sentence in reversed(sentences):
            if overlap_length + len(sentence) <= self.config.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_length += len(sentence)
            else:
                break
        
        return ' '.join(overlap_sentences)
    
    def _create_chunk_dict(self, text: str, document_id: str, page_num: int, chunk_id: int) -> Dict[str, Any]:
        """Create a standardized chunk dictionary."""
        return {
            'text': text,
            'document_id': document_id,
            'chunk_id': f"{document_id}_chunk_{chunk_id:04d}",
            'metadata': {
                'page': page_num,
                'length': len(text),
                'chunk_index': chunk_id
            }
        }
