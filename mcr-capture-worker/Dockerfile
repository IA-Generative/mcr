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

# Install Google Chrome (includes native H.264 codec support)
RUN apt-get update && apt-get install -y wget gnupg && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
      | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
      > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Install Playwright Chromium dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright
RUN uv run playwright install-deps chromium

COPY /mcr_capture_worker mcr_capture_worker

# Development with hot reload
FROM build AS dev

RUN uv sync --group dev

EXPOSE 7004
CMD ["uv", "run", "watchmedo", "auto-restart", "--pattern=*.py", "--recursive", "--directory=/app/mcr_capture_worker", "--", "uv", "run", "debugpy", "--listen", "0.0.0.0:7004", "-m", "mcr_capture_worker.worker"]


FROM build AS production

CMD ["uv", "run", "-m", "mcr_capture_worker.worker"]
