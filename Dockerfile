FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=/app/vendor

WORKDIR /app

# Install dependencies first for layer caching.
COPY pip_requirements.txt /app/pip_requirements.txt
RUN pip install --no-cache-dir -r pip_requirements.txt

# Copy application code (vendor + backend + frontend bundle).
COPY backend /app/backend
COPY vendor /app/vendor
COPY frontend/dist /app/frontend/dist

# Cache + creds mount points.
RUN mkdir -p /app/cache /etc/brick-labels

EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
