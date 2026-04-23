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
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# Install PulseAudio with a null sink so the browser AudioContext can initialize
# Install FFmpeg for the Webex Node bot audio encoding
RUN apt-get update && \
    apt-get install -y --no-install-recommends pulseaudio ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 (needed by @roamhq/wrtc native bindings)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY /mcr_capture_worker mcr_capture_worker

# Install Node dependencies for the Webex bot (ignore lockfile to get
# correct platform-specific native binaries for linux)
RUN cd mcr_capture_worker/services/audio/webex_node && npm install --omit=dev --package-lock=false
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
