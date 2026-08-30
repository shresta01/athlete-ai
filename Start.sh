#!/bin/bash
set -e

echo "=========================================="
echo "Seeding the knowledge base..."
echo "=========================================="
python seed_athlete_db.py

echo "=========================================="
echo "Starting Biomechanics Agent (8001)..."
echo "=========================================="
python trainers/biomechanics_trainer.py &

echo "=========================================="
echo "Starting Nutrition RAG Agent (8002)..."
echo "=========================================="
python trainers/nutrition_trainer.py &

echo "=========================================="
echo "Starting Progressive Overload Agent (8003)..."
echo "=========================================="
python trainers/overload_trainer.py &

echo "=========================================="
echo "Starting Central Orchestrator (8000)..."
echo "LLM_PROVIDER=${LLM_PROVIDER:-not set — check your"
echo "Render environment variables if chat fails}"
echo "=========================================="
python athlete_orchestrator.py &

# Give the 4 backend services a moment to bind their ports before
# Streamlit starts making requests to them.
sleep 5

echo "=========================================="
echo "Starting Streamlit UI on Render's assigned port..."
echo "=========================================="

streamlit run athlete_ui.py \
  --server.port "${PORT:-8501}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false