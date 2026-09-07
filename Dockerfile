FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY main.py ./
COPY data ./data

RUN pip install --no-cache-dir .

# Overridable at `docker run` time to size workers for the host - not a
# formula off CPU count, since this app's per-request cost is dominated by
# waiting on Pinecone/Anthropic network calls rather than CPU work, and each
# worker loads its own copy of the embedding model into memory.
ENV WEB_CONCURRENCY=2

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY} -b 0.0.0.0:8000 src.api:app"]
