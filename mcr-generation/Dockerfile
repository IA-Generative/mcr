FROM python:3.13.5-slim AS build

EXPOSE 8003

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

COPY certificate/cert-ollama.pem /usr/local/share/ca-certificates/cert-ollama.crt

RUN apt-get update && apt-get install -y ca-certificates curl && update-ca-certificates

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Download the latest installer, install it and then remove it
ADD https://astral.sh/uv/install.sh /install.sh
# Force install path of uv to /bin (otherwise going to /root/.local/bin
ENV UV_INSTALL_DIR=/bin
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh

WORKDIR /app

COPY ./pyproject.toml .
RUN uv sync

COPY /mcr_generation mcr_generation

COPY /certificate certificate
RUN chmod +x ./certificate/cert-config.sh && ./certificate/cert-config.sh

# Development with hot reload
FROM build AS dev

RUN uv sync --all-extras

EXPOSE 7003
CMD ["uv", "run", "watchmedo", "auto-restart", "--pattern=*.py", "--recursive", "--directory=/app/mcr_generation", "--", "uv", "run", "debugpy", "--listen", "0.0.0.0:7003", "-m", "celery", "-A", "mcr_generation.main", "worker"]


FROM build AS production

CMD ["uv", "run", "celery", "-A", "mcr_generation.main", "worker"]
