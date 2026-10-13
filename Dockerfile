FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir ".[web]"

# Default: run the delta check CLI in interactive list-analytes mode
# Override CMD at runtime for other commands, e.g.:
#   docker run delta-check-analyzer python cli.py check --analyte sodium --current 145 --previous 140
CMD ["python", "cli.py", "list-analytes"]
