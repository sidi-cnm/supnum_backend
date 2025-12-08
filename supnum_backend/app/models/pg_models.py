"""
SQLAlchemy models for PostgreSQL database.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.postgres import Base

class Document(Base):
    """
    Document table - stores metadata about indexed documents.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(1000), nullable=True)  # URL or file path
    doc_type = Column(String(50), default="text")  # text, pdf, html, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title[:50]}...')>"


class Chunk(Base):
    """
    Chunk table - stores text chunks with metadata.
    Each chunk is embedded and stored in Qdrant.
    """
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    chunk_size = Column(Integer, nullable=False)  # Length of chunk
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to document
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"


class QueryLog(Base):
    """
    Query log table - stores user queries and results for analytics.
    """
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    chunks_retrieved = Column(Integer, default=0)
    avg_score = Column(Float, nullable=True)
    response_time = Column(Float, nullable=True)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<QueryLog(id={self.id}, question='{self.question[:50]}...')>"