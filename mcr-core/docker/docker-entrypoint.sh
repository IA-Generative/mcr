#!/bin/sh
# Role dispatcher: one image, the process selected at run time.
#
# compose passes the role via `command:`, k8s via `args:` — so the commands and
# their flags stay versioned with the code instead of living in deploy manifests.
# `exec` keeps the chosen process as PID 1, which is what makes SIGTERM (remapped
# to SIGQUIT for the worker's cold shutdown) reach Celery rather than this shell.
set -e

case "${1:-api}" in
api)
    exec python -m uvicorn mcr_meeting.main:app --host 0.0.0.0 --port 8001
    ;;
worker)
    exec python -m celery -A mcr_meeting.transcription_worker worker -l info
    ;;
migrate)
    exec alembic upgrade head
    ;;
sweep-stale-captures)
    exec python -m mcr_meeting.sweep_stale_captures
    ;;
*)
    # escape hatch: any other command runs as given (debug shells, one-off scripts)
    exec "$@"
    ;;
esac
