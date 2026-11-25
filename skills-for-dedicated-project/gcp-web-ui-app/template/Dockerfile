# Web UI app for Cloud Run (see deploy.sh). Standard library only; runs/ is mounted from a Cloud Storage bucket.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 RUNS_DIR=/app/runs HOST=0.0.0.0
WORKDIR /app
# COPY requirements.txt . && RUN pip install --no-cache-dir -r requirements.txt   <- only if the domain needs a package
COPY app app
COPY docs docs
RUN mkdir -p runs
CMD exec python -m app --host 0.0.0.0 --port ${PORT:-8080}
