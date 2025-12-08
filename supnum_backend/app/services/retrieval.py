"""
Retrieval service for searching and retrieving relevant document chunks.
"""
from sqlalchemy.orm import Session
from app.models.pg_models import Chunk, Document
from app.utils.embeddings import generate_embedding
from app.db.qdrant_client import search_vectors
from typing import List, Dict, Tuple
import time

def retrieve_relevant_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5
) -> List[Tuple[Chunk, float]]:
    """
    Retrieve the most relevant chunks for a given query.
    
    Args:
        db: Database session
        query: User's question
        top_k: Number of chunks to retrieve
        score_threshold: Minimum similarity score (0-1)
    
    Returns:
        List of (Chunk, score) tuples
    """
    start_time = time.time()
    
    # 1. Generate query embedding
    print(f"🔍 Searching for: '{query}'")
    query_vector = generate_embedding(query)
    
    # 2. Search Qdrant for similar vectors
    results = search_vectors(
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold
    )
    
    if not results:
        print("❌ No relevant chunks found")
        return []
    
    # 3. Get chunk IDs from results
    chunk_ids = [result.id for result in results]
    
    # 4. Fetch full chunks from PostgreSQL
    chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    
    # 5. Create a mapping for quick lookup
    chunk_map = {chunk.id: chunk for chunk in chunks}
    
    # 6. Combine results with scores
    chunk_score_pairs = []
    for result in results:
        chunk = chunk_map.get(result.id)
        if chunk:
            chunk_score_pairs.append((chunk, result.score))
    
    elapsed = time.time() - start_time
    print(f"✅ Retrieved {len(chunk_score_pairs)} chunks in {elapsed:.2f}s")
    for i, (chunk, score) in enumerate(chunk_score_pairs, 1):
        print(f"   {i}. Score: {score:.3f} - {chunk.chunk_text[:80]}...")
    
    return chunk_score_pairs

def retrieve_chunks_with_context(
    db: Session,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
    context_chunks: int = 1
) -> List[Tuple[Chunk, float, List[Chunk]]]:
    """
    Retrieve chunks with surrounding context (previous and next chunks).
    
    Args:
        db: Database session
        query: User's question
        top_k: Number of chunks to retrieve
        score_threshold: Minimum similarity score
        context_chunks: Number of surrounding chunks to include on each side
    
    Returns:
        List of (main_chunk, score, context_chunks) tuples
    """
    # Get main chunks
    main_chunks = retrieve_relevant_chunks(db, query, top_k, score_threshold)
    
    results = []
    for chunk, score in main_chunks:
        # Get surrounding chunks
        context = db.query(Chunk).filter(
            Chunk.document_id == chunk.document_id,
            Chunk.chunk_index >= chunk.chunk_index - context_chunks,
            Chunk.chunk_index <= chunk.chunk_index + context_chunks
        ).order_by(Chunk.chunk_index).all()
        
        results.append((chunk, score, context))
    
    return results

def search_chunks_by_text(
    db: Session,
    search_text: str,
    limit: int = 10
) -> List[Chunk]:
    """
    Simple text-based search in chunks (fallback or complement to vector search).
    
    Args:
        db: Database session
        search_text: Text to search for
        limit: Maximum number of results
    
    Returns:
        List of matching chunks
    """
    chunks = db.query(Chunk).filter(
        Chunk.chunk_text.ilike(f"%{search_text}%")
    ).limit(limit).all()
    
    return chunks

def get_document_chunks(db: Session, document_id: int) -> List[Chunk]:
    """
    Get all chunks for a specific document.
    
    Args:
        db: Database session
        document_id: Document ID
    
    Returns:
        List of chunks ordered by index
    """
    chunks = db.query(Chunk).filter(
        Chunk.document_id == document_id
    ).order_by(Chunk.chunk_index).all()
    
    return chunks

def format_context_for_llm(chunks_with_scores: List[Tuple[Chunk, float]]) -> str:
    """
    Format retrieved chunks into a context string for LLM.
    
    Args:
        chunks_with_scores: List of (Chunk, score) tuples
    
    Returns:
        Formatted context string
    """
    if not chunks_with_scores:
        return ""
    
    context_parts = []
    context_parts.append("Contexte pertinent trouvé dans la base de connaissances:\n")
    
    for i, (chunk, score) in enumerate(chunks_with_scores, 1):
        # Get document info if available
        doc_info = ""
        if chunk.document:
            doc_info = f" [Source: {chunk.document.title}]"
        
        context_parts.append(f"\n--- Extrait {i} (Pertinence: {score:.2f}){doc_info} ---")
        context_parts.append(chunk.chunk_text)
    
    context_parts.append("\n---\n")
    
    return "\n".join(context_parts)

def deduplicate_chunks(chunks_with_scores: List[Tuple[Chunk, float]]) -> List[Tuple[Chunk, float]]:
    """
    Remove duplicate chunks from the same document that are adjacent.
    
    Args:
        chunks_with_scores: List of (Chunk, score) tuples
    
    Returns:
        Deduplicated list
    """
    if not chunks_with_scores:
        return []
    
    seen = set()
    unique_chunks = []
    
    for chunk, score in chunks_with_scores:
        # Create a unique key based on document and chunk index
        key = (chunk.document_id, chunk.chunk_index)
        if key not in seen:
            seen.add(key)
            unique_chunks.append((chunk, score))
    
    return unique_chunks