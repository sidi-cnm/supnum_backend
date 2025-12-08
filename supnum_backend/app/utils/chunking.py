"""
Text chunking utilities for splitting documents into processable chunks.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) == 0:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # Calculate end position
        end = start + chunk_size
        
        # If this is not the last chunk, try to break at a sentence or word boundary
        if end < text_length:
            # Look for sentence boundaries (. ! ?)
            for delimiter in ['. ', '! ', '? ', '\n\n', '\n']:
                last_delimiter = text.rfind(delimiter, start, end)
                if last_delimiter != -1:
                    end = last_delimiter + len(delimiter)
                    break
            else:
                # If no sentence boundary, look for word boundary
                last_space = text.rfind(' ', start, end)
                if last_space != -1:
                    end = last_space
        
        # Extract chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap if end < text_length else text_length
    
    return chunks

def chunk_text_by_sentences(text: str, max_sentences: int = 5) -> List[str]:
    """
    Split text into chunks by sentences.
    
    Args:
        text: The text to chunk
        max_sentences: Maximum number of sentences per chunk
    
    Returns:
        List of text chunks
    """
    # Simple sentence splitting (can be improved with NLTK or spaCy)
    sentences = []
    current = ""
    
    for char in text:
        current += char
        if char in '.!?' and len(current.strip()) > 10:
            sentences.append(current.strip())
            current = ""
    
    if current.strip():
        sentences.append(current.strip())
    
    # Group sentences into chunks
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        chunk = ' '.join(sentences[i:i + max_sentences])
        if chunk:
            chunks.append(chunk)
    
    return chunks

def chunk_text_by_paragraphs(text: str, max_paragraphs: int = 3) -> List[str]:
    """
    Split text into chunks by paragraphs.
    
    Args:
        text: The text to chunk
        max_paragraphs: Maximum number of paragraphs per chunk
    
    Returns:
        List of text chunks
    """
    # Split by double newlines (paragraph boundaries)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # Group paragraphs into chunks
    chunks = []
    for i in range(0, len(paragraphs), max_paragraphs):
        chunk = '\n\n'.join(paragraphs[i:i + max_paragraphs])
        if chunk:
            chunks.append(chunk)
    
    return chunks

def smart_chunk(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Intelligently chunk text using multiple strategies.
    
    This function tries to:
    1. First split by paragraphs if they're reasonable size
    2. Then by sentences if paragraphs are too large
    3. Finally by characters with overlap as fallback
    
    Args:
        text: The text to chunk
        chunk_size: Target size for chunks
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) == 0:
        return []
    
    # Try paragraph-based chunking first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # If adding this paragraph keeps us under chunk_size, add it
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            # Save current chunk if it exists
            if current_chunk:
                chunks.append(current_chunk)
            
            # If paragraph itself is too large, chunk it
            if len(para) > chunk_size:
                sub_chunks = chunk_text(para, chunk_size, overlap)
                chunks.extend(sub_chunks[:-1])  # Add all but last
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = para
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks