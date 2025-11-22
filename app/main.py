from fastapi import FastAPI
from app.routes import api

app = FastAPI(title="Chatbot SupNum")

# inclure routes
app.include_router(api.router)

@app.get("/")
def root():
    return {"message": "Bienvenue dans le Chatbot SupNum"}
