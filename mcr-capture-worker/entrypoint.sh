#!/bin/bash
set -e

setup_virtual_audio_sink() {
    rm -rf /tmp/pulse-* /tmp/.pulse-cookie 2>/dev/null || true
    pulseaudio --daemonize --start --exit-idle-time=-1 2>/dev/null || true
    pactl load-module module-null-sink sink_name=dummy sink_properties=device.description="Dummy_Output" 2>/dev/null || true
}

setup_virtual_audio_sink
exec "$@"
