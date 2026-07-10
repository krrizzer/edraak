FROM node:20-slim AS ui-builder

WORKDIR /ui
COPY ui/package*.json ./
RUN npm install
COPY ui/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV USE_BIGQUERY=true
ENV USE_GEMINI=true
ENV VERTEX_LOCATION=global
ENV GEMINI_MODEL=gemini-2.5-flash-lite

WORKDIR /app
COPY app/requirements.txt ./app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ ./app/
COPY --from=ui-builder /ui/dist ./app/static

# Train the placeholder risk model on synthetic data at build time (see risk_model.py).
RUN python -m app.functions.risk_model

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
