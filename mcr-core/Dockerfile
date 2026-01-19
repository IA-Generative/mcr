FROM python:3.12.10-slim AS build

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg build-essential curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download the latest installer, install it and then remove it
ADD https://astral.sh/uv/install.sh /install.sh
# Force install path of uv to /bin (otherwise going to /root/.local/bin
ENV UV_INSTALL_DIR=/bin
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh

WORKDIR /app

COPY ./pyproject.toml .
# Install only base (shared) dependencies here.
# Extra dependencies (e.g., for API or dev) are installed later in each specific image.
# This allows Docker to cache shared layers and reuse them across builds, speeding up image creation.
RUN uv sync
ENV VENV_LOCATION="/app/.venv"
ENV PATH="${VENV_LOCATION}/bin:$PATH"

FROM build AS api-dev

RUN uv sync --extra api --group dev
COPY ./alembic.ini .    
COPY /mcr_meeting mcr_meeting

EXPOSE 7001
EXPOSE 8001

# Using uv in dev images because pure python could't start debugpy out of the box
# with the current setup
CMD ["uv", "run", "debugpy", "--listen", "0.0.0.0:7001", "-m", "uvicorn", "mcr_meeting.main:app", "--host", "0.0.0.0", "--port","8001","--reload"]

# API service
FROM build AS api

RUN uv sync --extra api
# see above comment about COPY
COPY ./alembic.ini .
COPY /mcr_meeting mcr_meeting

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "mcr_meeting.main:app", "--host", "0.0.0.0", "--port", "8001"]

FROM build AS worker-dev

RUN uv sync --extra worker --group dev
# see above comment about COPY
COPY /mcr_meeting mcr_meeting

EXPOSE 7002

CMD ["watchmedo", "auto-restart", "--pattern=*.py", "--recursive", "--directory=/app/mcr_meeting", "--", "uv", "run", "--no-sync", "debugpy", "--listen", "0.0.0.0:7002", "-m", "celery", "-A", "mcr_meeting.transcription_worker", "worker", "-l", "info"]

FROM build AS worker

RUN uv sync --extra worker
# see above comment about COPY
COPY /mcr_meeting mcr_meeting      

# Add CUDA (GPU) binaries to LD_LIBRARY_PATH
# These are included with the PyTorch installation,
# but other libraries (e.g., faster-whisper) also need to access them.
# We are doing this to avoid managing 2 different installs of the binaries
ENV PYTHON_MINOR="${PYTHON_VERSION%.*}"
ENV LD_LIBRARY_PATH="${VENV_LOCATION}/lib/python${PYTHON_MINOR}/site-packages/nvidia/cublas/lib:${VENV_LOCATION}/lib/python${PYTHON_MINOR}/site-packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"


CMD ["python", "-m", "celery", "-A", "mcr_meeting.transcription_worker", "worker", "-l", "info"]
