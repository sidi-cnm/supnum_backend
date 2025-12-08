"""
Qdrant vector database client configuration.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "supnum_chunks")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "384"))  # all-MiniLM-L6-v2 default

# Initialize Qdrant client
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=30
)

def init_collection():
    """
    Initialize Qdrant collection if it doesn't exist.
    """
    try:
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if COLLECTION_NAME not in collection_names:
            # Create collection
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Created Qdrant collection: {COLLECTION_NAME}")
        else:
            print(f"✅ Qdrant collection already exists: {COLLECTION_NAME}")
            
    except Exception as e:
        print(f"❌ Error initializing Qdrant collection: {e}")
        raise

def get_qdrant_client():
    """
    Get Qdrant client instance.
    """
    return qdrant_client

def search_vectors(query_vector: list, limit: int = 5, score_threshold: float = 0.5):
    """
    Search for similar vectors in Qdrant.
    
    Args:
        query_vector: The query embedding vector
        limit: Number of results to return
        score_threshold: Minimum similarity score (0-1)
    
    Returns:
        List of search results with scores and payloads
    """
    try:
        results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
        return results
    except Exception as e:
        print(f"❌ Error searching vectors: {e}")
        return []

def upsert_vectors(points: list):
    """
    Insert or update vectors in Qdrant.
    
    Args:
        points: List of PointStruct objects
    """
    try:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"✅ Upserted {len(points)} vectors to Qdrant")
    except Exception as e:
        print(f"❌ Error upserting vectors: {e}")
        raise

def delete_by_document_id(document_id: int):
    """
    Delete all vectors for a specific document.
    
    Args:
        document_id: The document ID to delete
    """
    try:
        qdrant_client.delete(
            collection_name=COLLECTION_NAME,
            points_selector={
                "filter": {
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"value": document_id}
                        }
                    ]
                }
            }
        )
        print(f"✅ Deleted vectors for document_id: {document_id}")
    except Exception as e:
        print(f"❌ Error deleting vectors: {e}")
        raise