from __future__ import annotations

import argparse
import contextlib
import json
import os
import resource
import sys
import traceback
from pathlib import Path


MODELS: dict[str, object] = {}


def check(engine: str) -> None:
    if engine == "chatterbox":
        from chatterbox.tts import ChatterboxTTS  # noqa: F401
    elif engine == "kokoro":
        import kokoro_mlx  # noqa: F401
    elif engine == "breeze":
        model_path = Path(os.environ.get("SHADOW_LEARN_BREEZE_MODEL", ""))
        if not (model_path / "breeze_mlx" / "__init__.py").is_file():
            raise FileNotFoundError(f"Breeze model bundle is incomplete: {model_path}")
        if not (model_path / "weights.safetensors").is_file():
            raise FileNotFoundError(f"Breeze weights are missing: {model_path}")
        sys.path.insert(0, str(model_path))
        import mlx  # noqa: F401
        from breeze_mlx import BreezeMLXRuntime  # noqa: F401
    else:
        raise ValueError(f"Unknown worker engine {engine}")


def chatterbox(payload: dict) -> None:
    import soundfile as sf
    import torch
    from chatterbox.tts import ChatterboxTTS

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = MODELS.get("chatterbox")
    if model is None:
        model = ChatterboxTTS.from_pretrained(device=device)
        MODELS["chatterbox"] = model
    voice = payload.get("voice") or {}
    options = payload.get("options") or {}
    kwargs = {
        "exaggeration": float(options.get("expressiveness", 0.5)),
        "cfg_weight": float(options.get("cfg_weight", 0.5)),
    }
    if voice.get("processed_path"):
        kwargs["audio_prompt_path"] = voice["processed_path"]
    wav = model.generate(payload["text"], **kwargs)
    audio = wav.detach().to("cpu").float().numpy()
    if audio.ndim == 2:
        audio = audio.T
    sf.write(payload["output"], audio, model.sr, subtype="PCM_16")


def kokoro(payload: dict) -> None:
    from kokoro_mlx import KokoroTTS

    model = MODELS.get("kokoro")
    if model is None:
        model = KokoroTTS.from_pretrained()
        MODELS["kokoro"] = model
    voice = (payload.get("voice") or {}).get("id", "kokoro-af-heart").removeprefix("kokoro-").replace("-", "_")
    result = model.generate(payload["text"], voice=voice, speed=float(payload.get("options", {}).get("pace", 1)))
    audio = result.audio
    sample_rate = result.sample_rate
    import soundfile as sf

    sf.write(payload["output"], audio, sample_rate)


def breeze(payload: dict) -> None:
    import numpy as np
    import soundfile as sf

    model_path = Path(os.environ["SHADOW_LEARN_BREEZE_MODEL"])
    if str(model_path) not in sys.path:
        sys.path.insert(0, str(model_path))
    from breeze_mlx import BreezeMLXRuntime, GenerationConfig, MLXCodec, encode_reference

    options = payload.get("options") or {}
    voice = payload.get("voice") or {}
    runtime = MODELS.get("breeze")
    if runtime is None:
        codec = MLXCodec(model_path)
        runtime = BreezeMLXRuntime(
            model_path,
            codec=codec,
            generation=GenerationConfig(
                max_new_tokens=int(options.get("max_new_tokens", 1500)),
                chunk_frames=int(options.get("chunk_frames", 4)),
                first_chunk_frames=1,
                temperature=float(options.get("temperature", 0.9)),
                top_k=int(options.get("top_k", 50)),
                top_p=float(options.get("top_p", 1.0)),
                repetition_penalty=float(options.get("repetition_penalty", 1.1)),
            ),
        )
        MODELS["breeze"] = runtime
    runtime.gen.max_new_tokens = int(options.get("max_new_tokens", 1500))
    runtime.gen.chunk_frames = int(options.get("chunk_frames", 4))
    runtime.gen.temperature = float(options.get("temperature", 0.9))
    runtime.gen.depth_temperature = runtime.gen.temperature
    runtime.gen.top_k = int(options.get("top_k", 50))
    runtime.gen.depth_top_k = runtime.gen.top_k
    runtime.gen.top_p = float(options.get("top_p", 1.0))
    runtime.gen.depth_top_p = runtime.gen.top_p
    runtime.gen.repetition_penalty = float(options.get("repetition_penalty", 1.1))

    description = str(voice.get("description") or options.get("voice_description") or "").strip()
    accent = str(options.get("accent_direction") or "").strip()
    direction = str(options.get("direction") or "Speak clearly and naturally.").strip()
    accent_instruction = f"Use a natural {accent} accent." if accent else ""
    instruction = " ".join(part for part in (description, accent_instruction, direction) if part)
    request = {"text": payload["text"], "instruction": instruction, "speaker": "S0"}
    template = "tts_instruction"
    audio_codes = None
    if voice.get("processed_path"):
        reference_text = str(voice.get("reference_text") or "").strip()
        if not reference_text:
            raise ValueError("An exact reference transcript is required for Breeze cloning")
        request["ref_text"] = reference_text
        template = "ref_edit_tata"
        audio_codes = encode_reference(voice["processed_path"])

    mode = str(options.get("mode", "design"))
    cfg_default = 1.0 if mode == "clone" else 4.0
    base_seed = int(options.get("seed", 42))
    audio = np.zeros(0, np.float32)
    # Voice design can occasionally sample EOS as its first token for a valid
    # prompt. Retry only that empty result with deterministic alternate seeds.
    for seed in (base_seed, base_seed + 1, base_seed + 17):
        parts = [
            chunk.audio
            for chunk in runtime.stream(
                request,
                template=template,
                cfg_scale=float(options.get("cfg_scale", cfg_default)),
                seed=seed,
                audio_codes=audio_codes,
            )
            if chunk.audio.size
        ]
        audio = np.concatenate(parts) if parts else np.zeros(0, np.float32)
        if audio.size:
            break
    if not audio.size:
        raise RuntimeError("Breeze returned no audio after retrying valid sampling seeds")
    sf.write(payload["output"], audio, runtime.codec.sample_rate, subtype="PCM_16")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine", nargs="?")
    parser.add_argument("--check")
    args = parser.parse_args()
    if args.check:
        check(args.check)
        return
    handlers = {"chatterbox": chatterbox, "kokoro": kokoro, "breeze": breeze}
    if args.engine not in handlers:
        raise SystemExit("Unsupported engine")
    protocol_stdout = sys.stdout
    for line in sys.stdin:
        try:
            payload = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                handlers[args.engine](payload)
            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            response = {"ok": True, "peak_rss_bytes": peak_rss}
        except Exception as exc:
            response = {"ok": False, "error": str(exc), "trace": traceback.format_exc()}
        print(json.dumps(response), file=protocol_stdout, flush=True)


if __name__ == "__main__":
    main()
