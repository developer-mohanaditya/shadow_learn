# ShadowLearn V2 — Breeze setup

V2 runs Breeze-compatible speech generation locally on Apple Silicon through the Vireo TTS 3B MLX mixed 4-bit bundle. It does not send scripts, reference voices, or generated audio to a hosted speech API.

## What V2 adds

- Voice design from a natural-language description.
- Instant voice cloning from a 3–60 second reference and its exact transcript.
- Directed cloned speech with emotion, pace, delivery, accent, and vocal-event instructions.
- English and Chinese generation.
- Open-ended English accent directions, including General American and Indian English.
- The V1 waveform, phrase highlighting, history, recovery, WAV, and MP3 workflow.
- A blue V2 interface that can be switched back to V1 Classic at any time.

## Install

1. Use an Apple Silicon Mac and install `uv`, Python 3.12, Node.js, `ffmpeg`, Git, and the Hugging Face CLI.
2. Sign in to Hugging Face and accept the licence shown on the Vireo model page:

   ```sh
   hf auth login
   ```

3. From the repository root, install the application dependencies:

   ```sh
   uv sync --extra dev
   cd frontend
   npm install
   cd ..
   ```

4. Install the local Breeze runtime, main model, and voice-cloning encoder:

   ```sh
   ./scripts/install-breeze.sh
   ```

   The script creates `.engines/breeze/` and downloads model data under `data-v2/models/`. Both locations are excluded from Git. The initial download is several gigabytes.

5. Build and verify the app:

   ```sh
   cd frontend && npm run build && cd ..
   uv run pytest -q
   ```

6. Run V2 beside an unchanged V1 production service:

   ```sh
   ./scripts/run-v2-staging.sh
   ```

7. Open [http://127.0.0.1:8421/v2](http://127.0.0.1:8421/v2). V1 can continue running independently at `http://127.0.0.1:8420`.

## Using voice design

Open **Breeze Studio → Voice Design**, select English or Chinese, and describe the voice. For English, select a common accent direction or write a reusable designed voice in **Voice Lab**. Add performance direction for pace, emotion, pauses, emphasis, and vocal events, then generate.

## Using voice cloning

1. Open **Voice Lab → Clone from audio**.
2. Choose a clean 3–60 second WAV, MP3, or M4A recording with one speaker.
3. Enter the exact transcript, including every spoken word.
4. Confirm ownership or explicit permission and save the voice.
5. Use **Instant Clone** for neutral similarity or **Directed Clone** for stronger acting control.

The first use encodes and caches the local reference. Later uses reuse the cache and are substantially faster.

## Storage and privacy

The staging setup uses `data-v2/`, separate from V1 data. It contains the SQLite database, model files, reference recordings, cached reference codes, and generated audio. Do not commit this directory to a public repository.

Internet access is required only to install packages and download the model files. Normal speech generation uses the local MLX/PyTorch workers and ShadowLearn's localhost API.

## Performance expectations

Generation speed depends on text length and whether the model is already loaded. A cold first voice-design request includes model loading. A warm short request on the development M5 Max completed faster than real time. The first cloned-voice request also performs a one-time reference encoding; cached clone requests are much faster.
