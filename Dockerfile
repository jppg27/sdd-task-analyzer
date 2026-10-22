# Imagem de execução do Test Harness do TaskAnalyzer (Fase 3).
#
# Base leve e imutável: python:<versão>-slim. A versão padrão é a 3.12, mínima
# exigida pelo CONTEXT_RULES; outra versão pode ser testada com
#   docker build --build-arg PYTHON_VERSION=3.11 .
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências primeiro: a camada só é refeita quando requirements.txt muda.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código, testes e configuração das ferramentas (pytest, cobertura e ruff).
COPY pyproject.toml ./
COPY src/ src/
COPY tests/ tests/

# Executa como usuário sem privilégios de root.
RUN useradd --create-home --uid 1000 taskanalyzer \
    && chown -R taskanalyzer:taskanalyzer /app
USER taskanalyzer

# Comando de entrada principal: o Test Harness.
CMD ["pytest", "tests/test_harness.py", "-v"]
