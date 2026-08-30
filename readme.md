---
title: Athlete AI
emoji: 🏋️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Athlete AI

A LangGraph-orchestrated fitness coaching platform: FastAPI backend,
RAG-augmented nutrition guidance (ChromaDB + Ollama embeddings),
progressive-overload tracking, and a Streamlit frontend — all
collapsed into one container for Hugging Face's free Docker Spaces
(which, unlike your local docker-compose setup, only supports a
single Dockerfile at the repo root — no multi-container compose).

## What to push here

This folder only has the two Space-specific files (Dockerfile,
start.sh) plus this README. Push your ENTIRE existing athlete
project folder alongside them — same structure as your local repo:

- athlete_orchestrator.py
- athlete_ui.py
- requirements.txt              (yours — don't replace with a guess)
- seed_athlete_db.py
- trainers/
  - biomechanics_trainer.py
  - nutrition_trainer.py
  - overload_trainer.py
- athlete_runbooks/              (whatever seed_athlete_db.py reads)
- .streamlit/config.toml         (for the PWA static-serving setup)
- static/                        (manifest.json, service-worker.js, icons)

Don't push venv/, __pycache__/, .vscode/, or athlete_chroma_db/ —
add those to a .gitignore. athlete_chroma_db/ gets rebuilt fresh by
seed_athlete_db.py on every container start anyway.

Your existing docker/ folder and docker-compose.yml aren't used by
this Space at all — HF only reads the Dockerfile at the repo root.
Keep them in your repo for local development if you still use
docker-compose there; they just won't affect the Space.

## Differences from your local docker-compose setup

- One container, not five. Ollama + all 3 trainer workers + the
  orchestrator + Streamlit all run as background processes inside
  a single container (see start.sh), since Spaces only builds one
  Dockerfile.
- CPU-only. Your compose reserved an nvidia GPU for Ollama — HF's
  free tier has none. Defaulted to llama3.2:1b instead of the
  llama3:3b in your compose (which isn't a real Ollama tag anyway)
  to keep CPU inference responsive.
- URLs are all 127.0.0.1, not Docker service hostnames like
  http://ollama:11434 — everything's on localhost now since it's
  one container.

## First boot

The first request after a fresh build is slow — the container pulls
both Ollama models and runs your seeding script before anything's
ready to serve. Subsequent requests (until the Space sleeps and
rebuilds) are fast.