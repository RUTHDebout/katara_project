# ── Image de base Python slim (légère et rapide) ──
FROM python:3.11-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# Copier d'abord requirements pour profiter du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code KATARA
COPY . .

# Cloud Run injecte la variable PORT automatiquement
ENV PORT=8080

# Lancer avec gunicorn (production-ready)
CMD exec gunicorn katara_api:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info
