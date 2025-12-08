"""
Main FastAPI application for SupNum Chatbot.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import api
from app.db.postgres import init_db
from app.db.qdrant_client import init_collection
import os

# Create FastAPI app
app = FastAPI(
    title="SupNum Chatbot API",
    description="RAG-based chatbot for SupNum using PostgreSQL, Qdrant, and OpenRouter",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api.router)

@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Bienvenue dans le Chatbot SupNum",
        "version": "1.0.0",
        "endpoints": {
            "ask": "/ask - Ask a question",
            "documents": "/documents - Manage documents",
            "search": "/search - Search chunks",
            "stats": "/stats - System statistics",
            "health": "/health - Health check",
            "docs": "/docs - API documentation"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize database and Qdrant collection on startup."""
    print("\n" + "="*60)
    print("🚀 Starting SupNum Chatbot API")
    print("="*60 + "\n")
    
    try:
        # Initialize PostgreSQL
        print("📊 Initializing PostgreSQL database...")
        init_db()
        
        # Initialize Qdrant collection
        print("🔍 Initializing Qdrant collection...")
        init_collection()
        
        print("\n" + "="*60)
        print("✅ All systems initialized successfully!")
        print("="*60 + "\n")
        
        print("📝 API Documentation: http://localhost:8000/docs")
        print("🔍 Alternative docs: http://localhost:8000/redoc")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during startup: {e}\n")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("\n👋 Shutting down SupNum Chatbot API\n")