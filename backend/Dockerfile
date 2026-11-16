FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Actualiza paquetes del sistema para reducir vulnerabilidades (Trivy)
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

# Usuario sin privilegios (buena práctica de seguridad)
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# El mismo contenedor ejecuta las migraciones cuando el pipeline
# sobrescribe el comando con: alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
