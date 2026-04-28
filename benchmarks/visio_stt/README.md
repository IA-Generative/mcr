# Visio STT Benchmark

Tool for evaluating Visio's native STT (visio.numerique.gouv.fr) by injecting
multiple audio files in parallel into as many distinct meetings.

Each task spawns a Playwright-driven Chromium instance that joins a meeting as
a guest, disables the camera, keeps the microphone open, and lets Chromium
stream the WAV via `--use-file-for-fake-audio-capture`. No recording happens
on the bot side — the transcription is collected directly from Visio's UI.

## Prerequisites

- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- `ffmpeg` available in `PATH` (used by `preprocess.py`)
- Playwright browsers installed

## Installation

```bash
cd benchmarks/visio_stt
uv sync
uv run playwright install chromium
```

## Audio pipeline

The benchmark uses a strict two-step audio pipeline:

```
test_audio/raw/         ← drop your source audios here (any format)
        │
        │   preprocess.py
        ▼
test_audio/processed/   ← WAV 16 kHz mono 16-bit PCM (consumed by run.py)
```

### 1. Drop sources in `test_audio/raw/`

Place every source audio file you want to benchmark in `test_audio/raw/`.
Any format `ffmpeg` can decode is fine (mp3, m4a, ogg, wav...).

### 2. Convert with `preprocess.py`

Chromium's `--use-file-for-fake-audio-capture` flag **only** accepts WAV files
in **16 kHz, mono, 16-bit PCM**. Anything else streams silence to the meeting
without raising an error, so `preprocess.py` enforces the format strictly.

```bash
uv run python preprocess.py test_audio/raw test_audio/processed
```

This reads every file in `test_audio/raw/`, converts it to the required WAV
format, validates the output, and writes it to `test_audio/processed/`.

### 3. Reference processed files in the config

`run.py` reads audio paths from `config.json` — they should point to files
inside `test_audio/processed/`.

## Configure the tasks

One task = one audio + one Visio URL. See `config.example.json` for examples.
Each URL must point to a **different** meeting, otherwise bots transcribe over
each other.

Minimal `config.json`:

```json
{
  "headless": true,
  "post_stream_buffer_s": 3.0,
  "tasks": [
    {"audio": "test_audio/processed/example.wav", "url": "https://visio.numerique.gouv.fr/xxx-yyyy-zzz"}
  ]
}
```

Fields:

- `headless` (bool, default `true`) — hide or show the Chromium windows
- `post_stream_buffer_s` (float, default `3.0`) — seconds to wait after the
  stream ends, to let Visio finalize its transcription
- `tasks[].audio` — path to a WAV file (resolved relative to the cwd)
- `tasks[].url` — Visio meeting URL

Audio paths are validated at startup: `.wav` extension required, file must
exist.

## Run the benchmark

From `benchmarks/visio_stt/`:

```bash
# Validation only (config + audios), without launching browsers
uv run python run.py --config config.json --validate-only

# Full run
uv run python run.py --config config.json

# Run with visible windows (debug)
uv run python run.py --config config.json --no-headless
```

Each bot streams the entire audio, waits an extra `post_stream_buffer_s`
seconds, then closes the browser cleanly. The Visio transcription must then
be collected manually from each meeting's UI.

## Layout

```
bot.py              # One Playwright bot (one per task)
run.py              # Orchestrator: pre-flight + parallel launch
preprocess.py       # ffmpeg conversion → WAV 16 kHz mono 16-bit
config.py           # Pydantic models
config.example.json # Configuration examples
test_audio/raw/         # Source audios (you provide)
test_audio/processed/   # Output of preprocess.py, input of run.py
```

## Notes

- Playwright selectors (`NAME_INPUT_SELECTOR`, `JOIN_BUTTON_NAME`, etc.) in
  `bot.py` are aligned with `mcr-capture-worker`'s `VisioStrategy`. Keep them
  in sync if Visio's UI changes.
- `--lang=en-US` is passed to Chromium to pin the Visio UI language and ensure
  selectors based on button names match.
- The waiting-room timeout is 5 minutes (`WAITING_ROOM_TIMEOUT_MS`).
