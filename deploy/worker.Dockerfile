# O worker compartilha o pacote da API de propósito: jobs são casos de uso do mesmo
# domínio, não uma segunda implementação das regras (topology_decision.md).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN pip install --upgrade pip && pip install -e apps/api

COPY apps/api/app apps/api/app
COPY apps/worker/worker apps/worker/worker

# `app` é a API, `worker` é o worker. Se os dois se chamassem `app`, o primeiro do
# PYTHONPATH sombrearia o outro e este container subiria a API sem ninguém notar.
ENV PYTHONPATH=/srv/apps/api:/srv/apps/worker

# `data/` existe na imagem, e vazio, para o volume nomeado nascer com o dono certo:
# Docker copia dono e permissão do diretório da imagem ao criar o volume, e sem isto ele
# nasceria de root e o processo sem privilégio não conseguiria gravar o relatório.
RUN mkdir -p /srv/data && useradd --create-home --uid 10001 app && chown -R app:app /srv
USER app

CMD ["python", "-m", "worker.main"]
