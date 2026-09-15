# PhishGuard — single-container image for Hugging Face Spaces (Docker SDK).
# Serves the FastAPI backend + built React bundle from one origin (:7860).
# The ML artifact (*.pkl) is NOT baked in — upload it to the Space separately
# (see README "Hugging Face" section) or run with the heuristic fallback.

# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Same-origin prod: fetch /predict directly (dev uses the /api Vite proxy).
ENV VITE_API_BASE=""
RUN npm run build

# ---- Stage 2: Python backend ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    CORS_ORIGINS=* \
    ALLOW_HEURISTIC_FALLBACK=true \
    DATABASE_URL=sqlite:///./phishguard.db \
    MODEL_PATH=models/best_model.pkl \
    MODEL_METADATA_PATH=ml/comparison_report.json
WORKDIR /app/backend
COPY phishing_detector/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY phishing_detector/backend/ ./
COPY --from=frontend /build/dist ./frontend_dist
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
