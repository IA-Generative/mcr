FROM python:3.13.3-slim AS build

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y curl
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Download the latest installer, install it and then remove it
ADD https://astral.sh/uv/install.sh /install.sh
# Force install path of uv to /bin (otherwise going to /root/.local/bin
ENV UV_INSTALL_DIR=/bin
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh

WORKDIR /app

COPY ./pyproject.toml .
RUN uv sync

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright
RUN uv run playwright install firefox
RUN uv run playwright install-deps firefox

# Download OpenH264 GMP plugin (Cisco) for WebRTC H.264 support in Firefox
# Architecture-aware: aarch64 vs x86_64
RUN apt-get update && \
    apt-get install -y --no-install-recommends unzip && \
    mkdir -p /opt/gmp-gmpopenh264/2.6.0 && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
        OPENH264_URL="https://ciscobinary.openh264.org/openh264-linux64-aarch64-652bdb7719f30b52b08e506645a7322ff1b2cc6f.zip"; \
    else \
        OPENH264_URL="https://ciscobinary.openh264.org/openh264-linux64-652bdb7719f30b52b08e506645a7322ff1b2cc6f.zip"; \
    fi && \
    curl -sL "$OPENH264_URL" -o /tmp/openh264-gmp.zip && \
    unzip /tmp/openh264-gmp.zip -d /opt/gmp-gmpopenh264/2.6.0/ && \
    rm /tmp/openh264-gmp.zip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
ENV MOZ_GMP_PATH=/opt/gmp-gmpopenh264/2.6.0

# Install PulseAudio with a null sink so Firefox AudioContext can initialize
RUN apt-get update && \
    apt-get install -y --no-install-recommends pulseaudio && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY /mcr_capture_worker mcr_capture_worker
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Development with hot reload
FROM build AS dev

RUN uv sync --group dev

EXPOSE 7004
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uv", "run", "watchmedo", "auto-restart", "--pattern=*.py", "--recursive", "--directory=/app/mcr_capture_worker", "--", "uv", "run", "debugpy", "--listen", "0.0.0.0:7004", "-m", "mcr_capture_worker.worker"]


FROM build AS production

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uv", "run", "-m", "mcr_capture_worker.worker"]
