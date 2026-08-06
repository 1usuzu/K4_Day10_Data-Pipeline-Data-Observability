from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from core.config import load_settings, require_llm_credentials
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question

# Initialize FastAPI App
app = FastAPI(title="Agentic RAG API")

# Mount static folder
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Global state for agent
class AppState:
    agent = None
    index_type = "None"

state = AppState()

class ChatRequest(BaseModel):
    message: str

@app.on_event("startup")
def startup_event():
    print("Initializing AI Core...")
    settings = load_settings()
    require_llm_credentials(settings)
    
    # Ưu tiên load index REPAIRED
    if settings.paths.repaired_embeddings_json.exists():
        index_path = settings.paths.repaired_embeddings_json
        state.index_type = "REPAIRED"
    elif settings.paths.embeddings_json.exists():
        index_path = settings.paths.embeddings_json
        state.index_type = "BASELINE"
    else:
        raise FileNotFoundError("No vector index found! Please run phase 1 first.")
        
    index = LocalEmbeddingIndex.load(settings, index_path)
    state.agent = build_agent(settings, index)
    print(f"Connected to {state.index_type} database successfully!")

@app.get("/", response_class=HTMLResponse)
def get_index():
    # Serve the index.html directly from the root
    index_file = static_dir / "index.html"
    return index_file.read_text(encoding="utf-8")

@app.post("/api/chat")
def chat(request: ChatRequest):
    if not state.agent:
        raise HTTPException(status_code=500, detail="Agent is not initialized.")
    try:
        response = run_agent_question(state.agent, request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("script.web_api:app", host="127.0.0.1", port=8000, reload=True)
