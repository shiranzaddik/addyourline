# ---- Single-container production image ----
# Builds the React frontend, then serves it (and the API + WebSockets) from one
# FastAPI/uvicorn process on a single domain (https://addyourline.com).

# Stage 1: build the frontend.
FROM node:24-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: backend runtime that also serves the built frontend.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# frontend.py expects the built assets at ../frontend/dist relative to backend/.
COPY --from=frontend /build/dist /app/frontend/dist

EXPOSE 8000
# Honor the platform-provided $PORT if set (Render/Railway/Fly), else 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
