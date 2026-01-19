# Load environment variables before anything else in the package
from pathlib import Path

from dotenv import load_dotenv

# Resolve path to .env.local.host in project root (2 levels up from this file)
# This is used only when running code in this package in local dev on the host machine
# The rest of the time (docker-compose or kubernetes), the env is loaded
# from system ENV VARS
ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local.host"
# Will fail gracefully if ENV_FILE did not resolve
load_dotenv(ENV_FILE)
