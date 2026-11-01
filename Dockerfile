# Una sola imagen para entrenamiento y backend. Usar la misma imagen garantiza
# que el preprocesamiento y las versiones de librerías sean idénticas en ambos
# lados, así el pipeline serializado se carga sin fricciones.

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero: esta capa se cachea mientras solo cambie el código.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY params.yaml ./
COPY data ./data
COPY src ./src
COPY api ./api

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Imagen de desarrollo: tests y notebook encima de runtime.
FROM runtime AS dev

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

COPY tests ./tests
COPY notebooks ./notebooks

CMD ["pytest", "-q"]
