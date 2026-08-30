FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Brings in athlete_orchestrator.py, athlete_ui.py, trainers/,
# seed_athlete_db.py, athlete_runbooks/, .streamlit/, static/
COPY . .

RUN chmod +x start.sh

# Render injects its own $PORT at runtime and routes traffic to
# whatever port your service actually listens on — start.sh reads
# it rather than a fixed number.
CMD ["./start.sh"]