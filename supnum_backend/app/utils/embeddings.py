"""
Embedding generation utilities using sentence-transformers.
"""
from sentence_transformers import SentenceTransformer
import os
from typing import List, Union
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Model configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "384"))

# Initialize model (lazy loading)
_model = None

def get_embedding_model():
    """
    Get or initialize the embedding model (singleton pattern).
    """
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}...")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✅ Model loaded successfully (dimension: {VECTOR_SIZE})")
    return _model

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Input text
    
    Returns:
        Embedding vector as list of floats
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Generate embeddings for multiple texts efficiently.
    
    Args:
        texts: List of input texts
        batch_size: Batch size for processing
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = get_embedding_model()
    
    # Process in batches
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 10,
        convert_to_numpy=True
    )
    
    return [emb.tolist() for emb in embeddings]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Cosine similarity score (0-1)
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    
    return float(dot_product / (norm_v1 * norm_v2))

def semantic_search(query: str, corpus: List[str], top_k: int = 5) -> List[tuple]:
    """
    Perform semantic search on a corpus of texts.
    
    Args:
        query: Search query
        corpus: List of texts to search
        top_k: Number of top results to return
    
    Returns:
        List of (index, score, text) tuples
    """
    model = get_embedding_model()
    
    # Generate embeddings
    query_embedding = model.encode(query, convert_to_numpy=True)
    corpus_embeddings = model.encode(corpus, convert_to_numpy=True)
    
    # Calculate similarities
    similarities = []
    for idx, corpus_emb in enumerate(corpus_embeddings):
        score = cosine_similarity(query_embedding.tolist(), corpus_emb.tolist())
        similarities.append((idx, score, corpus[idx]))
    
    # Sort by score and return top k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]

# Preload model on import (optional, comment out if you want lazy loading)
# get_embedding_model()