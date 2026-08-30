from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import os
import chromadb
from chromadb.utils import embedding_functions

app = FastAPI(title="High-Performance Nutrition & Knowledge RAG Specialist")

chroma_client = chromadb.PersistentClient(path="athlete_chroma_db")

# ------------------------------------------------------------
# EMBEDDINGS: switched from Ollama's nomic-embed-text to
# ChromaDB's bundled local embedding model (all-MiniLM-L6-v2).
#
# Why: this file previously called out to a local Ollama server
# for embeddings. On a free host with no GPU and ~512MB-1GB RAM
# (e.g. Render's free tier), there's no Ollama server to call —
# running one there isn't viable at all. DefaultEmbeddingFunction
# downloads a small (~80MB) sentence-transformers model ONCE and
# runs it in-process on CPU — no separate service, no API key, no
# network call per request, and light enough for a free-tier box.
#
# IMPORTANT: seed_athlete_db.py MUST use this same embedding
# function (not OllamaEmbeddingFunction) — a collection's queries
# only make sense when seeded and queried with the same embedder.
# ------------------------------------------------------------

embedding_fn = embedding_functions.DefaultEmbeddingFunction()

collection = None

try:

    collection = chroma_client.get_collection(
        name="athlete_knowledge_base",
        embedding_function=embedding_fn
    )

    print(
        "[Nutrition RAG] Loaded collection "
        "'athlete_knowledge_base'."
    )

except Exception as e:

    print(
        "[Nutrition RAG] WARNING: could not load "
        "'athlete_knowledge_base' "
        f"({type(e).__name__}: {e}). "
        "Run seed_athlete_db.py first — until then, "
        "/fuel-plan will return empty context."
    )


class AthleteStateRequest(BaseModel):
    raw_workout_input: str
    parsed_workout_metrics: Dict = {}
    nutrition_rag_context: List[str] = []
    physiological_assessment: str = ""
    next_action_routine: List[str] = []

@app.post("/fuel-plan")
async def fuel_plan(state: AthleteStateRequest):
    print("[RAG Node] Querying local vector store for matching protocols...")

    if collection is None:

        print(
            "[RAG Node] Collection not loaded — "
            "returning empty context."
        )

        return {"nutrition_rag_context": []}

    results = collection.query(
        query_texts=[state.raw_workout_input],
        n_results=4
    )

    context_chunks = results.get("documents", [[]])[0]
    return {"nutrition_rag_context": context_chunks}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)