"""
Pydantic models for API validation and serialization.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# Document schemas
class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    source: Optional[str] = None
    doc_type: str = Field(default="text", max_length=50)

class DocumentResponse(BaseModel):
    id: int
    title: str
    source: Optional[str]
    doc_type: str
    created_at: datetime
    chunk_count: int = 0
    
    class Config:
        from_attributes = True

# Chunk schemas
class ChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_text: str
    chunk_index: int
    score: Optional[float] = None  # Similarity score when retrieved
    
    class Config:
        from_attributes = True

# Query schemas
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    use_context: bool = Field(default=True)

class QuestionResponse(BaseModel):
    question: str
    answer: str
    chunks_used: List[ChunkResponse]
    response_time: float
    model_used: str

# Search schemas
class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

class SearchResponse(BaseModel):
    query: str
    results: List[ChunkResponse]
    total_found: int

# Stats schema
class StatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_queries: int
    avg_response_time: Optional[float]
    collection_name: str
    vector_size: int