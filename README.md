# ShadowLearn

ShadowLearn is a free, local-first English shadowing studio for Apple Silicon Macs. Paste or upload a script, choose a local voice, generate natural speech, and practise alongside waveform playback and phrase-synchronised text.

> **V2 Breeze preview:** the `v2-breeze` branch adds a separate blue Breeze TTS 2 experience with voice design, instant cloning, directed performance, English and Chinese, and open-ended accent directions. V1 remains available through the version switch. See the [V2 Breeze setup guide](docs/V2_BREEZE.md).

All normal inference, history, voice references, previews, and audio files stay on your Mac. ShadowLearn does not require ElevenLabs, OpenAI, Supabase, or another paid/cloud inference API.

## Features

- Speech Studio for typed, pasted, `.txt`, and `.md` scripts up to 25,000 characters.
- Kokoro MLX preset voices for fast US and UK English generation.
- ZONOS2 Metal and Chatterbox adapters for expressive speech and instant voice cloning.
- ElevenLabs-inspired Voice Library with locally generated, cached voice previews.
- WAV masters and MP3 playback/download copies.
- Waveform scrubbing, phrase regions, click-to-seek, repeat phrase, and 0.75–1.25× playback.
- Spotify-style current-phrase highlighting and automatic scrolling.
- Persistent SQLite history, resumable phrase jobs, safe deletion, and local backups.
- Installable React PWA served by a FastAPI backend.
- Optional `launchd` startup and private Tailscale access.

## Supported platform

Version 1.0 targets an Apple Silicon Mac running macOS. The included ZONOS2 setup uses its native Metal implementation; CUDA, Windows, Linux, and Intel Macs are not currently supported by the provided service scripts.

Recommended hardware:

- Apple Silicon Mac with at least 16 GB unified memory.
- 32 GB or more for experimenting with expressive/cloning engines.
- Enough free storage for model weights and generated audio.

## How it works

```text
Browser/PWA
    │
    ▼
FastAPI on 127.0.0.1:8420
    ├── SQLite and local audio under data/
    ├── Kokoro MLX worker
    ├── Chatterbox MPS worker
    └── ZONOS2 Metal server on 127.0.0.1:1919
```

The `/api` routes are ShadowLearn's own local endpoints. Internet access is needed to install dependencies and download models, but not for normal generation after installation. Tailscale is optional and provides private networking rather than speech inference or cloud storage.

## Step-by-step installation

### 1. Install system prerequisites

Install the Apple command-line tools:

```sh
xcode-select --install
```

Install [Homebrew](https://brew.sh/) if it is not already available, then install the required tools:

```sh
brew install python@3.11 uv node ffmpeg git
```

Confirm the commands are available:

```sh
python3 --version
uv --version
node --version
npm --version
ffmpeg -version
```

### 2. Clone ShadowLearn

```sh
git clone https://github.com/developer-mohanaditya/shadow_learn.git
cd shadow_learn
```

### 3. Install application dependencies

Create the Python environment and install the backend/test dependencies:

```sh
uv sync --extra dev
```

Install the frontend dependencies:

```sh
cd frontend
npm install
cd ..
```

### 4. Run the app without neural models

ShadowLearn includes a macOS system-voice adapter so the complete workflow can be tested before downloading model weights:

```sh
./scripts/dev.sh
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Choose a system voice, enter a short script, generate it, and verify playback. Press `Control-C` in the terminal when finished.

### 5. Install local speech engines

Install all three supported engines:

```sh
./scripts/install-engines.sh all
```

Or install them individually:

```sh
./scripts/install-engines.sh kokoro
./scripts/install-engines.sh chatterbox
./scripts/install-engines.sh zonos2
```

What each engine provides:

| Engine | Primary use | Notes |
| --- | --- | --- |
| Kokoro MLX | Fast preset voices | Recommended for everyday shadow practice |
| ZONOS2 Metal | Expressive speech and cloning | Runs through a local Metal server |
| Chatterbox MPS | Expressive speech and cloning | Slower on the hardware tested for v1 |
| macOS System | Setup verification | No neural-model download required |

The first model run may download weights from the model publisher. These files remain local afterward. Review each upstream model's licence before using or redistributing its output.

### 6. Download and test ZONOS2

After installing ZONOS2, download its Q4_K model and start a temporary local server:

```sh
./.engines/zonos2/start-zonos2.sh --quant q4_k --gpu -y --no-browser -- --dac-gpu
```

In another terminal, confirm that the local service responds:

```sh
curl http://127.0.0.1:1919/health
```

Stop the temporary server with `Control-C` after the check. The production `launchd` setup in step 9 starts it automatically.

### 7. Build and test ShadowLearn

```sh
./scripts/build.sh
```

This creates the production frontend and runs the backend test suite. You can also run the quality checks directly:

```sh
uv run pytest -q
uv run ruff check backend tests
cd frontend && npm run build && cd ..
```

### 8. Start the production server manually

Start ZONOS2 in one terminal if you intend to use it, then run ShadowLearn in another:

```sh
uv run shadow-learn
```

Open [http://127.0.0.1:8420](http://127.0.0.1:8420).

The application deliberately binds only to localhost. Persistent files are created under `data/`, including the SQLite database, audio, voice references, uploads, models, backups, and recoverable temporary files.

### 9. Start automatically with macOS

After the frontend is built and the desired engines are installed:

```sh
./scripts/install-service.sh
```

This installs per-user `launchd` agents for ShadowLearn and, when installed, ZONOS2. Check them with:

```sh
launchctl print gui/$(id -u)/com.shadowlearn.app
launchctl print gui/$(id -u)/com.shadowlearn.zonos2
```

Application logs are stored in `data/shadowlearn.log` and `data/shadowlearn-error.log`. ZONOS2 logs are stored in `data/zonos2.log` and `data/zonos2-error.log`.

### 10. Optional private remote access

Install and sign in to [Tailscale](https://tailscale.com/download/mac), then run:

```sh
./scripts/tailscale-serve.sh
```

Use the private URL printed by Tailscale from another device in the same tailnet. The Mac must be powered on and awake for generation and playback.

## Using ShadowLearn

1. Open **Speech Studio**.
2. Type, paste, or upload a UTF-8 `.txt` or `.md` script.
3. Select an available voice and engine.
4. Choose the accent, pace, mood, and expressiveness supported by that engine.
5. Optionally add `[pause:short]`, `[pause:medium]`, `[pause:long]`, or `[emphasis]text[/emphasis]` cues.
6. Generate the speech and follow progress phrase by phrase.
7. Play the result, click phrases to seek, repeat the current phrase, or adjust playback speed.
8. Reopen completed generations from **History** without running inference again.

In **Voice Library**, click the play button to hear a preset voice. The first preview is generated locally and cached; later playback is immediate. To clone a voice, upload or record 10–30 seconds of clean speech and confirm that you own the voice or have explicit permission to use it.

## Benchmarking engines

For structured release testing, use the [V1 acceptance checklist](docs/V1_ACCEPTANCE_CHECKLIST.md), [four-engine test guide](docs/ENGINE_TEST_GUIDE.md), and the prepared scripts under [`test-scripts/`](test-scripts/).

Run every engine against the fixed English corpus:

```sh
uv run shadow-benchmark run kokoro
uv run shadow-benchmark run zonos2
uv run shadow-benchmark run chatterbox
```

Results and audio are written under `data/benchmarks/<run-id>`. After listening, record subjective scores:

```sh
uv run shadow-benchmark score <run-id> \
  --naturalness 4.5 \
  --pronunciation 4.5 \
  --prosody 4.0 \
  --punctuation 4.5 \
  --clone-similarity 4.0
```

On the original M5 Max test machine, Kokoro averaged an RTF of 0.0584, ZONOS2 Q4_K with GPU DAC averaged 0.970, and Chatterbox averaged 2.217. Performance will vary by hardware, model version, script, and settings.

## Data, backups, and privacy

- `data/shadowing.db` is the authoritative SQLite database.
- `data/audio/` stores phrase files, WAV masters, and MP3 copies.
- `data/voices/` stores voice references, working copies, embeddings, and previews.
- `data/uploads/` retains source files.
- `data/models/` stores downloaded model files and caches.
- `data/backups/` contains local database backups.
- `data/tmp/` contains recoverable incomplete writes.

The entire `data/` directory is ignored by Git. Do not commit voice recordings, generated audio, model weights, databases, or logs to a public repository. Use **Settings → Backup** for application backups and separately back up the project volume for protection from disk failure.

## Troubleshooting

### ZONOS2 says “not reachable”

Check whether it responds locally:

```sh
curl http://127.0.0.1:1919/health
launchctl print gui/$(id -u)/com.shadowlearn.zonos2
tail -n 100 data/zonos2-error.log
```

Reinstall/start its service if necessary:

```sh
./scripts/install-engines.sh zonos2
./scripts/install-service.sh
```

### An engine is unavailable

Open **Settings** to see engine health and its reported reason. Confirm that its isolated runtime exists under `.engines/`, then reinstall only that engine.

### Port 8420 is already in use

If the `launchd` service is already running, use [http://127.0.0.1:8420](http://127.0.0.1:8420) instead of starting another production process.

### Resetting development dependencies

It is safe to recreate `.venv/`, `.engines/`, `frontend/node_modules/`, and `frontend/dist/`. Do not remove `data/` unless you intentionally want to permanently delete all history, voices, models, audio, and backups.

## Development layout

```text
backend/shadowlearn/   FastAPI, SQLite, jobs, audio, and engine adapters
benchmark/             Fixed benchmark corpus
deploy/                launchd templates
frontend/src/          React/TypeScript PWA
scripts/               Setup, build, service, and Tailscale helpers
tests/                 Backend unit and integration tests
```

## Current v1 boundaries

ShadowLearn v1 does not include pronunciation scoring, gamification, progress tracking, public accounts, sharing, cloud storage, PDF/DOCX extraction, multilingual generation, LoRA training, or voice fine-tuning.

## Responsible voice cloning

Only clone your own voice or a voice you have explicit permission to use. Do not use ShadowLearn to impersonate, deceive, harass, or infringe the rights of another person.

## Acknowledgements

ShadowLearn integrates local adapters for [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [Chatterbox](https://huggingface.co/ResembleAI/chatterbox), and the Apple Metal implementation of [ZONOS2](https://github.com/Zyphra/zonos2.cpp). Waveform playback uses [Wavesurfer.js](https://wavesurfer.xyz/).

## Status

This is the initial public **ShadowLearn V1.0** release. It is a personal-use, local-first project and should be treated as early software: retain backups and review upstream model licences before broader use.
