FROM python:3.12.10-slim AS build

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

COPY ./mcr_gateway mcr_gateway

# Development with hot reload
FROM build AS dev

RUN uv sync --group dev

EXPOSE 5678
EXPOSE 8000
CMD ["uv", "run", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "mcr_gateway.main:app", "--host", "0.0.0.0", "--port" ,"8000", "--reload"]  


FROM build AS production

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "mcr_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
