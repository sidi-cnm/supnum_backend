from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
def ask_question(req: QuestionRequest):
    # ici tu appelleras query_handler.py pour Postgres + Qdrant
    return {"answer": f"Vous avez demandé : {req.question}"}
