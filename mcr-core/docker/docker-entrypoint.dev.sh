#!/bin/sh
# Development role dispatcher — same roles as docker-entrypoint.sh, so
# `command: ["worker"]` means the same thing locally and in production.
#
# Deliberately NOT a copy of the prod entrypoint: each role here wraps the app in
# debugpy (and watchmedo for the worker, which must stay the parent process to
# restart its child). So dev does not reproduce prod's PID-1/signal behaviour —
# only the role contract is shared.
#
# Keep the role names in sync with docker-entrypoint.sh.
set -e

case "${1:-api}" in
api)
    exec uv run debugpy --listen 0.0.0.0:7001 -m uvicorn mcr_meeting.main:app \
        --host 0.0.0.0 --port 8001 --reload
    ;;
worker)
    exec watchmedo auto-restart --pattern=*.py --recursive --directory=/app/mcr_meeting \
        -- uv run --no-sync debugpy --listen 0.0.0.0:7002 \
        -m celery -A mcr_meeting.transcription_worker worker -l info
    ;;
migrate)
    exec uv run alembic upgrade head
    ;;
*)
    # escape hatch: any other command runs as given (debug shells, one-off scripts)
    exec "$@"
    ;;
esac
