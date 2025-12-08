"""
Query handler service - processes questions and generates answers using RAG.
Integrates with OpenRouter for access to open-source LLMs.
"""
from sqlalchemy.orm import Session
from app.services.retrieval import retrieve_relevant_chunks, format_context_for_llm, deduplicate_chunks
from app.models.pg_models import QueryLog
import os
import time
import requests
from typing import Dict, List, Tuple
from app.models.pg_models import Chunk
from dotenv import load_dotenv

load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model selection (you can change this to any model available on OpenRouter)
# Some good open-source options:
# - "meta-llama/llama-3.1-8b-instruct:free" (Free, good quality)
# - "mistralai/mistral-7b-instruct:free" (Free, fast)
# - "google/gemma-2-9b-it:free" (Free, good for French)
# - "meta-llama/llama-3.1-70b-instruct" (Paid but excellent)
# - "anthropic/claude-3-haiku" (Paid, very good)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

def generate_answer_with_llm(
    question: str,
    context: str,
    model: str = DEFAULT_MODEL,
    use_context: bool = True
) -> Dict[str, any]:
    """
    Generate an answer using OpenRouter LLM.
    
    Args:
        question: User's question
        context: Retrieved context from documents
        model: Model to use (OpenRouter model identifier)
        use_context: Whether to use retrieved context
    
    Returns:
        Dictionary with answer and metadata
    """
    # Construct prompt
    if use_context and context:
        system_prompt = """Tu es un assistant intelligent pour SupNum. 
Tu réponds aux questions en te basant sur le contexte fourni.
Si l'information n'est pas dans le contexte, dis-le clairement.
Sois précis, concis et utile. Réponds en français."""

        user_prompt = f"""{context}

Question: {question}

Réponds à la question en te basant sur le contexte ci-dessus. Si l'information n'est pas disponible dans le contexte, indique-le clairement."""
    else:
        system_prompt = """Tu es un assistant intelligent pour SupNum.
Réponds aux questions de manière utile et précise. Réponds en français."""
        
        user_prompt = question
    
    # Prepare API request
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",  # Optional, for rankings
        "X-Title": "SupNum Chatbot"  # Optional, shows in rankings
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        # Call OpenRouter API
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract answer
        answer = result["choices"][0]["message"]["content"]
        
        return {
            "answer": answer,
            "model": model,
            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
            "success": True
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling OpenRouter API: {e}")
        return {
            "answer": f"Désolé, je n'ai pas pu générer une réponse. Erreur: {str(e)}",
            "model": model,
            "tokens_used": 0,
            "success": False
        }

def handle_question(
    db: Session,
    question: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
    use_context: bool = True,
    model: str = DEFAULT_MODEL
) -> Dict:
    """
    Handle a user question end-to-end using RAG.
    
    Args:
        db: Database session
        question: User's question
        top_k: Number of chunks to retrieve
        score_threshold: Minimum similarity score
        use_context: Whether to use retrieved context
        model: LLM model to use
    
    Returns:
        Dictionary with answer and metadata
    """
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"❓ Question: {question}")
    print(f"{'='*60}\n")
    
    # Step 1: Retrieve relevant chunks
    chunks_with_scores = retrieve_relevant_chunks(
        db=db,
        query=question,
        top_k=top_k,
        score_threshold=score_threshold
    )
    
    # Deduplicate chunks
    chunks_with_scores = deduplicate_chunks(chunks_with_scores)
    
    # Step 2: Format context
    context = format_context_for_llm(chunks_with_scores) if use_context else ""
    
    # Step 3: Generate answer
    print(f"🤖 Generating answer with {model}...")
    llm_result = generate_answer_with_llm(
        question=question,
        context=context,
        model=model,
        use_context=use_context
    )
    
    # Step 4: Calculate stats
    response_time = time.time() - start_time
    avg_score = sum(score for _, score in chunks_with_scores) / len(chunks_with_scores) if chunks_with_scores else 0
    
    # Step 5: Log query
    query_log = QueryLog(
        question=question,
        answer=llm_result["answer"],
        chunks_retrieved=len(chunks_with_scores),
        avg_score=avg_score,
        response_time=response_time
    )
    db.add(query_log)
    db.commit()
    
    print(f"\n✅ Answer generated in {response_time:.2f}s")
    print(f"💬 Answer: {llm_result['answer'][:200]}...")
    print(f"{'='*60}\n")
    
    # Step 6: Prepare response
    return {
        "question": question,
        "answer": llm_result["answer"],
        "chunks_used": [
            {
                "id": chunk.id,
                "text": chunk.chunk_text,
                "score": score,
                "document_id": chunk.document_id,
                "document_title": chunk.document.title if chunk.document else None
            }
            for chunk, score in chunks_with_scores
        ],
        "response_time": response_time,
        "model_used": model,
        "chunks_retrieved": len(chunks_with_scores),
        "avg_similarity": avg_score,
        "tokens_used": llm_result.get("tokens_used", 0)
    }

def simple_answer(question: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a simple answer without RAG (useful for testing).
    
    Args:
        question: User's question
        model: LLM model to use
    
    Returns:
        Answer text
    """
    result = generate_answer_with_llm(
        question=question,
        context="",
        model=model,
        use_context=False
    )
    return result["answer"]

# Alternative: Using local models with Ollama (if preferred)
def generate_answer_with_ollama(
    question: str,
    context: str,
    model: str = "llama3.1",
    use_context: bool = True
) -> Dict[str, any]:
    """
    Alternative implementation using Ollama for local models.
    Install Ollama and run: ollama pull llama3.1
    
    Args:
        question: User's question
        context: Retrieved context
        model: Ollama model name
        use_context: Whether to use context
    
    Returns:
        Dictionary with answer and metadata
    """
    try:
        import requests
        
        if use_context and context:
            prompt = f"""Contexte:
{context}

Question: {question}

Réponds à la question en te basant sur le contexte ci-dessus."""
        else:
            prompt = question
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "answer": result["response"],
            "model": f"ollama/{model}",
            "tokens_used": 0,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Error calling Ollama: {e}")
        return {
            "answer": f"Erreur avec Ollama: {str(e)}",
            "model": model,
            "tokens_used": 0,
            "success": False
        }