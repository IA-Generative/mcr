FROM python:3.12.10-slim AS build

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Bytecode is compiled once at build time instead of on every container start.
# LINK_MODE=copy because hardlinking into a layer snapshot is unreliable — this is
# the case uv warns about, and kaniko (our CI builder) snapshots the filesystem.
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg build-essential curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ARG UV_VERSION=0.9.7
ADD https://astral.sh/uv/${UV_VERSION}/install.sh /install.sh
# Force install path of uv to /bin (otherwise going to /root/.local/bin
ENV UV_INSTALL_DIR=/bin
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh

WORKDIR /app

# Dependencies are installed BEFORE the source is copied, so a source-only change
# reuses this layer from the cache (kaniko caches it to the registry).
# --locked: resolve from uv.lock so an image can't drift from the committed
# resolution. --no-dev: dev groups are opt-in per stage (uv installs them by default).
COPY ./pyproject.toml ./uv.lock ./
RUN uv sync --locked --no-dev --extra api --extra worker
ENV VENV_LOCATION="/app/.venv"
ENV PATH="${VENV_LOCATION}/bin:$PATH"

# Runtime image — the venv and the app, nothing else: no uv, no compiler, no caches.
FROM python:3.12.10-slim AS prod

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ffmpeg is a runtime dependency: audio pre-processing shells out to it.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

# Left root-owned on purpose: the app user only reads /app, so no --chown pass over
# the venv (it rewrites every file), and the app tree stays read-only for it.
COPY --from=build /app/.venv /app/.venv
COPY ./alembic.ini .
COPY /mcr_meeting mcr_meeting
COPY ./docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER app

EXPOSE 8001

# One image for every role: compose passes the role via `command:`, k8s via `args:`,
# so the commands stay versioned with the code instead of in deploy manifests.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["api"]

# --- Development image (never built by the pipeline) --------------------------
# One image for every dev role, same role names as prod. It keeps uv so
# debugpy/watchmedo can start the app against a mounted source tree, and stays
# root so a mounted source tree needs no ownership juggling.

FROM build AS dev

RUN uv sync --locked --extra api --extra worker --group dev
COPY ./alembic.ini .
COPY /mcr_meeting mcr_meeting
COPY ./docker/docker-entrypoint.dev.sh /usr/local/bin/docker-entrypoint.dev.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.dev.sh

# 8001 app, 7001 api debugger, 7002 worker debugger (only the mapped one is used)
EXPOSE 8001
EXPOSE 7001
EXPOSE 7002

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.dev.sh"]
CMD ["api"]

# Flower monitoring UI — built on the same venv so its celery/kombu versions
# match the workers (mher/flower:latest is stale and breaks worker inspection).
# Runs standalone against the broker (no app import) to avoid pulling in the
# app's dependencies and its required settings.
FROM build AS flower

RUN uv pip install flower

EXPOSE 5555
CMD ["sh", "-c", "celery --broker=\"redis://${REDIS_HOST}:${REDIS_PORT}/0\" --result-backend=\"redis://${REDIS_HOST}:${REDIS_PORT}/1\" flower --address=0.0.0.0 --port=5555"]
