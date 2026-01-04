FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY ./requirements/base.txt /requirements/base.txt
COPY ./requirements/ingest.txt /requirements/ingest.txt

COPY ./src/core /src/core
COPY ./src/ingest /src/ingest

WORKDIR /src

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install -r /requirements/base.txt && \
    pip install -r /requirements/ingest.txt

CMD ["python", "-m", "ingest.sources.github.search.search_main"]
