"""
Script to re-index a specific document with improved TOC filtering.
Usage: python reindex_document.py <document_id>
"""
import sys
import os
from rag.config import RAGConfig
from rag.vector_store import VectorStore
from rag.chunking import TextChunker

def reindex_document(document_id: str):
    """Re-index a document by removing old vectors and adding new ones."""
    print(f"Re-indexing document: {document_id}")
    
    # Load config
    cfg = RAGConfig.from_env()
    
    # Remove old vectors
    print("Removing old vectors...")
    vs = VectorStore(cfg)
    removed = vs.remove_document(document_id)
    print(f"Removed {removed} old vectors")
    
    # Load processed text
    processed_path = os.path.join(cfg.processed_folder, f"{document_id}.txt")
    if not os.path.exists(processed_path):
        print(f"Error: Processed file not found: {processed_path}")
        return False
    
    print(f"Loading text from: {processed_path}")
    with open(processed_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    print(f"Text length: {len(text)} characters")
    
    # Chunk text
    print("Chunking text...")
    chunker = TextChunker(cfg)
    chunks = chunker.chunk_text(text, document_id)
    print(f"Created {len(chunks)} chunks")
    
    # Add to vector store (filter will be applied during retrieval)
    print("Adding chunks to vector store...")
    vs.add_documents(chunks)
    
    stats = vs.get_stats()
    print(f"\nDone! Vector store now has {stats['total_vectors']} total vectors")
    print(f"Unique documents: {stats['unique_documents']}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reindex_document.py <document_id>")
        print("\nAvailable documents:")
        cfg = RAGConfig.from_env()
        processed_dir = cfg.processed_folder
        if os.path.exists(processed_dir):
            for fname in os.listdir(processed_dir):
                if fname.endswith(".txt"):
                    doc_id = fname[:-4]
                    print(f"  - {doc_id}")
        sys.exit(1)
    
    document_id = sys.argv[1]
    success = reindex_document(document_id)
    sys.exit(0 if success else 1)
