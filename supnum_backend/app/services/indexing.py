"""
Indexing service for processing and storing documents with their embeddings.
"""
from sqlalchemy.orm import Session
from app.models.pg_models import Document, Chunk
from app.utils.chunking import smart_chunk
from app.utils.embeddings import generate_embeddings_batch
from app.db.qdrant_client import upsert_vectors, delete_by_document_id
from qdrant_client.models import PointStruct
from typing import List, Dict
import time

def index_document(
    db: Session,
    title: str,
    content: str,
    source: str = None,
    doc_type: str = "text"
) -> Document:
    """
    Index a document: chunk it, generate embeddings, and store in DB + Qdrant.
    
    Args:
        db: Database session
        title: Document title
        content: Document content
        source: Document source (URL, file path, etc.)
        doc_type: Type of document
    
    Returns:
        Created Document object
    """
    start_time = time.time()
    
    # 1. Create document record
    document = Document(
        title=title,
        content=content,
        source=source,
        doc_type=doc_type
    )
    db.add(document)
    db.flush()  # Get the document ID without committing
    
    print(f"📄 Created document: {title} (ID: {document.id})")
    
    # 2. Chunk the content
    chunks = smart_chunk(content)
    print(f"✂️  Created {len(chunks)} chunks")
    
    if not chunks:
        print("⚠️  No chunks created, skipping indexing")
        db.commit()
        return document
    
    # 3. Generate embeddings
    print("🧮 Generating embeddings...")
    embeddings = generate_embeddings_batch(chunks)
    
    # 4. Store chunks in PostgreSQL
    chunk_records = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_record = Chunk(
            document_id=document.id,
            chunk_text=chunk_text,
            chunk_index=idx,
            chunk_size=len(chunk_text)
        )
        db.add(chunk_record)
        chunk_records.append(chunk_record)
    
    db.flush()  # Get chunk IDs
    
    # 5. Store embeddings in Qdrant
    print("💾 Storing vectors in Qdrant...")
    points = []
    for chunk_record, embedding in zip(chunk_records, embeddings):
        point = PointStruct(
            id=chunk_record.id,
            vector=embedding,
            payload={
                "document_id": document.id,
                "chunk_index": chunk_record.chunk_index,
                "chunk_text": chunk_record.chunk_text[:500],  # Store preview
                "title": title,
                "source": source,
                "doc_type": doc_type
            }
        )
        points.append(point)
    
    upsert_vectors(points)
    
    # 6. Commit transaction
    db.commit()
    
    elapsed = time.time() - start_time
    print(f"✅ Document indexed successfully in {elapsed:.2f}s")
    print(f"   - Chunks: {len(chunks)}")
    print(f"   - Vectors: {len(points)}")
    
    return document

def delete_document(db: Session, document_id: int) -> bool:
    """
    Delete a document and all its chunks from PostgreSQL and Qdrant.
    
    Args:
        db: Database session
        document_id: ID of document to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            print(f"❌ Document {document_id} not found")
            return False
        
        # Delete from Qdrant
        delete_by_document_id(document_id)
        
        # Delete from PostgreSQL (cascades to chunks)
        db.delete(document)
        db.commit()
        
        print(f"✅ Deleted document {document_id} and all its chunks")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting document: {e}")
        return False

def reindex_document(db: Session, document_id: int) -> Document:
    """
    Reindex an existing document (useful if chunking/embedding logic changes).
    
    Args:
        db: Database session
        document_id: ID of document to reindex
    
    Returns:
        Updated Document object
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise ValueError(f"Document {document_id} not found")
    
    # Delete old vectors
    delete_by_document_id(document_id)
    
    # Delete old chunks
    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.commit()
    
    # Re-chunk and re-embed
    chunks = smart_chunk(document.content)
    embeddings = generate_embeddings_batch(chunks)
    
    # Store new chunks
    chunk_records = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_record = Chunk(
            document_id=document.id,
            chunk_text=chunk_text,
            chunk_index=idx,
            chunk_size=len(chunk_text)
        )
        db.add(chunk_record)
        chunk_records.append(chunk_record)
    
    db.flush()
    
    # Store new vectors
    points = []
    for chunk_record, embedding in zip(chunk_records, embeddings):
        point = PointStruct(
            id=chunk_record.id,
            vector=embedding,
            payload={
                "document_id": document.id,
                "chunk_index": chunk_record.chunk_index,
                "chunk_text": chunk_record.chunk_text[:500],
                "title": document.title,
                "source": document.source,
                "doc_type": document.doc_type
            }
        )
        points.append(point)
    
    upsert_vectors(points)
    db.commit()
    
    print(f"✅ Reindexed document {document_id}")
    return document

def get_indexing_stats(db: Session) -> Dict:
    """
    Get statistics about indexed documents and chunks.
    
    Args:
        db: Database session
    
    Returns:
        Dictionary with statistics
    """
    total_docs = db.query(Document).count()
    total_chunks = db.query(Chunk).count()
    
    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "avg_chunks_per_doc": total_chunks / total_docs if total_docs > 0 else 0
    }