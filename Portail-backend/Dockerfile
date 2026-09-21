# Image de production du backend Digital 360.
#
# Deux étages : le premier compile les dépendances (certaines roues comme
# asyncpg et bcrypt ont besoin d'un compilateur), le second ne garde que le
# résultat. L'image finale n'embarque donc aucun outil de compilation.

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install .


FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends libreoffice-impress fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# Un utilisateur non privilégié : si le processus est compromis, il n'a aucun
# droit sur l'hôte ni sur les volumes montés en lecture seule.
RUN useradd --create-home --uid 10001 digital360

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER digital360
WORKDIR /home/digital360
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status==200 else 1)"

# Un seul worker par conteneur : pour monter en charge on augmente le nombre de
# conteneurs (replicas), ce qui reste correct derrière le reverse proxy.
CMD ["uvicorn", "adgi360.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
