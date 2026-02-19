# Load environment variables before anything else in the package
from pathlib import Path

from dotenv import load_dotenv

# Resolve path to .env.local.host in project root (2 levels up from this file)
# This is used only when running code in this package in local dev on the host machine
# The rest of the time (docker-compose or kubernetes), the env is loaded
# from system ENV VARS

mcr_meeting_dir = Path(__file__).resolve().parents[2]

ENV_FILE = mcr_meeting_dir / ".env"
ENV_LOCAL_HOST_FILE = mcr_meeting_dir / ".env.local.host"
ENV_LOCAL_DOCKER_FILE = mcr_meeting_dir / ".env.local.docker"

# load_dotenv will ignore missing files
# so the order of loading allows for overrides without requiring all files to be present
load_dotenv(ENV_LOCAL_DOCKER_FILE, override=False)
load_dotenv(ENV_LOCAL_HOST_FILE, override=True)
load_dotenv(ENV_FILE, override=True)
