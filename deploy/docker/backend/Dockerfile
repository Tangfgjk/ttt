FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ /app/backend/

RUN pip install --upgrade pip \
    && pip install -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
