FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libpq-dev \
    gdal-bin \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY workers/ingest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system --gid 1001 workergroup \
 && adduser  --system --uid 1001 --ingroup workergroup workeruser

COPY --chown=workeruser:workergroup workers/ .

USER workeruser

CMD ["python", "-m", "ingest.epa.run"]
