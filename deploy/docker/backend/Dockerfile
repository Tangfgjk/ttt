FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com
ARG INSTALL_ML=true
ARG TORCH_PACKAGE=torch==2.3.1+cpu
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

WORKDIR /app/backend

RUN sed -i \
    -e 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
    -e 's|http://security.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
    /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md /app/backend/

RUN pip install --upgrade pip -i "${PYPI_INDEX_URL}" --trusted-host "${PYPI_TRUSTED_HOST}" \
    && python -c "import tomllib; from pathlib import Path; project = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']; Path('/tmp/backend-requirements.txt').write_text('\n'.join(project['dependencies']) + '\n', encoding='utf-8'); Path('/tmp/ml-requirements.txt').write_text('\n'.join(dep for dep in project['optional-dependencies']['ml'] if not dep.startswith('torch')) + '\n', encoding='utf-8')" \
    && pip install -r /tmp/backend-requirements.txt \
        -i "${PYPI_INDEX_URL}" \
        --trusted-host "${PYPI_TRUSTED_HOST}" \
    && if [ "${INSTALL_ML}" = "true" ]; then \
        echo "${TORCH_PACKAGE}" > /tmp/torch-constraints.txt \
        && pip install "${TORCH_PACKAGE}" --index-url "${TORCH_INDEX_URL}" \
        && pip install -r /tmp/ml-requirements.txt \
            -c /tmp/torch-constraints.txt \
            -i "${PYPI_INDEX_URL}" \
            --extra-index-url "${TORCH_INDEX_URL}" \
            --trusted-host "${PYPI_TRUSTED_HOST}"; \
    fi \
    && rm -f /tmp/backend-requirements.txt /tmp/ml-requirements.txt /tmp/torch-constraints.txt

COPY backend/ /app/backend/

RUN pip install -e . --no-deps

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
