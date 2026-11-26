# Build context: repository root (the API imports the ml/ package for inference).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# LightGBM needs the OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY ml/pyproject.toml ml/README.md ml/
COPY ml/src ml/src
COPY ml/artifacts ml/artifacts
RUN pip install ./ml

COPY apps/api/pyproject.toml apps/api/alembic.ini apps/api/
COPY apps/api/app apps/api/app
COPY apps/api/alembic apps/api/alembic
RUN pip install ./apps/api

WORKDIR /srv/apps/api
ENV HEALTHML_ARTIFACTS=/srv/ml/artifacts
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
