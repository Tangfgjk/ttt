FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN sed -i \
    -e 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
    -e 's|http://security.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
    /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md /app/backend/

RUN pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    && python -c "import tomllib; from pathlib import Path; deps = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['dependencies']; Path('/tmp/backend-requirements.txt').write_text('\n'.join(dep for dep in deps if not dep.startswith('torch')) + '\n', encoding='utf-8')" \
    && echo "torch==2.3.1+cpu" > /tmp/torch-cpu-constraints.txt \
    && pip install torch==2.3.1+cpu --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r /tmp/backend-requirements.txt \
        -c /tmp/torch-cpu-constraints.txt \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        --trusted-host mirrors.aliyun.com \
    && rm -f /tmp/backend-requirements.txt /tmp/torch-cpu-constraints.txt

COPY backend/ /app/backend/

RUN pip install -e . --no-deps

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
