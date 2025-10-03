# syntax=docker/dockerfile:1

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /app/frontend/dist ./frontend/dist

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
