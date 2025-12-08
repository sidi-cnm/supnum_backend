"""
API routes for the SupNum chatbot.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.postgres import get_db
from app.models.qdrant_models import (
    DocumentCreate, DocumentResponse, QuestionRequest, QuestionResponse,
    SearchRequest, SearchResponse, ChunkResponse, StatsResponse
)
from app.models.pg_models import Document, Chunk, QueryLog
from app.services.indexing import index_document, delete_document, get_indexing_stats
from app.services.query_handler import handle_question
from app.services.retrieval import retrieve_relevant_chunks, search_chunks_by_text
from app.db.qdrant_client import COLLECTION_NAME, VECTOR_SIZE
from sqlalchemy import func

router = APIRouter()

# ============================================================================
# QUESTION ANSWERING (Main RAG endpoint)
# ============================================================================

@router.post("/ask", response_model=QuestionResponse)
def ask_question(
    req: QuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question and get an AI-generated answer based on indexed documents.
    
    This is the main RAG endpoint that:
    1. Retrieves relevant chunks from the knowledge base
    2. Formats them as context
    3. Generates an answer using an LLM (via OpenRouter)
    """
    try:
        result = handle_question(
            db=db,
            question=req.question,
            top_k=req.top_k,
            score_threshold=req.score_threshold,
            use_context=req.use_context
        )
        
        # Convert to response model
        return QuestionResponse(
            question=result["question"],
            answer=result["answer"],
            chunks_used=[
                ChunkResponse(
                    id=chunk["id"],
                    document_id=chunk["document_id"],
                    chunk_text=chunk["text"],
                    chunk_index=0,  # Not needed in response
                    score=chunk["score"]
                )
                for chunk in result["chunks_used"]
            ],
            response_time=result["response_time"],
            model_used=result["model_used"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# ============================================================================
# DOCUMENT MANAGEMENT
# ============================================================================

@router.post("/documents", response_model=DocumentResponse)
def create_document(
    doc: DocumentCreate,
    db: Session = Depends(get_db)
):
    """
    Index a new document in the knowledge base.
    
    The document will be:
    1. Chunked into smaller pieces
    2. Embedded using sentence-transformers
    3. Stored in PostgreSQL (metadata) and Qdrant (vectors)
    """
    try:
        document = index_document(
            db=db,
            title=doc.title,
            content=doc.content,
            source=doc.source,
            doc_type=doc.doc_type
        )
        
        chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()
        
        return DocumentResponse(
            id=document.id,
            title=document.title,
            source=document.source,
            doc_type=document.doc_type,
            created_at=document.created_at,
            chunk_count=chunk_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all indexed documents.
    """
    documents = db.query(Document).offset(skip).limit(limit).all()
    
    result = []
    for doc in documents:
        chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
        result.append(
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                doc_type=doc.doc_type,
                created_at=doc.created_at,
                chunk_count=chunk_count
            )
        )
    
    return result

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific document.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()
    
    return DocumentResponse(
        id=document.id,
        title=document.title,
        source=document.source,
        doc_type=document.doc_type,
        created_at=document.created_at,
        chunk_count=chunk_count
    )

@router.delete("/documents/{document_id}")
def delete_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document and all its chunks.
    """
    success = delete_document(db, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": f"Document {document_id} deleted successfully"}

# ============================================================================
# SEARCH
# ============================================================================

@router.post("/search", response_model=SearchResponse)
def search(
    req: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for relevant chunks without generating an answer.
    
    Useful for:
    - Debugging retrieval
    - Building custom interfaces
    - Checking what context would be used
    """
    try:
        chunks_with_scores = retrieve_relevant_chunks(
            db=db,
            query=req.query,
            top_k=req.top_k,
            score_threshold=req.score_threshold
        )
        
        results = [
            ChunkResponse(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_text=chunk.chunk_text,
                chunk_index=chunk.chunk_index,
                score=score
            )
            for chunk, score in chunks_with_scores
        ]
        
        return SearchResponse(
            query=req.query,
            results=results,
            total_found=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")

# ============================================================================
# STATISTICS & MONITORING
# ============================================================================

@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """
    Get system statistics.
    """
    indexing_stats = get_indexing_stats(db)
    total_queries = db.query(QueryLog).count()
    avg_response_time = db.query(func.avg(QueryLog.response_time)).scalar()
    
    return StatsResponse(
        total_documents=indexing_stats["total_documents"],
        total_chunks=indexing_stats["total_chunks"],
        total_queries=total_queries,
        avg_response_time=avg_response_time,
        collection_name=COLLECTION_NAME,
        vector_size=VECTOR_SIZE
    )

@router.get("/health")
def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "SupNum Chatbot",
        "version": "1.0.0"
    }