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
ENV USE_ADK=false
ENV USE_GEMINI=false

WORKDIR /app
COPY app/requirements.txt ./app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ ./app/
COPY --from=ui-builder /ui/dist ./app/static

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
