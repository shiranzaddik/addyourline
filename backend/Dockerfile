FROM python:3.12-slim

WORKDIR /app

# System deps (kept minimal). build-essential only if a wheel needs compiling.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# In production, place the built frontend at ../frontend/dist to serve it from here,
# or run the frontend separately behind a reverse proxy.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
