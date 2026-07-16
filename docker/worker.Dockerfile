FROM python:3.12-slim

WORKDIR /app

# ingest.* and scoring.* both live under /app after COPY workers/
ENV PYTHONPATH=/app

# Prefer manylinux wheels (pyogrio/geopandas) over compiling GDAL from apt —
# full libgdal-dev frequently OOMs local Docker Desktop builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY workers/ingest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system --gid 1001 workergroup \
 && adduser  --system --uid 1001 --ingroup workergroup workeruser

COPY --chown=workeruser:workergroup workers/ .

USER workeruser

# Default: EPA; override via compose command (census, cms, scoring, fbi)
CMD ["python", "-m", "ingest.epa.run"]
