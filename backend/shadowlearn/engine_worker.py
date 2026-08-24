from __future__ import annotations

import argparse
import contextlib
import json
import resource
import sys
import traceback


MODELS: dict[str, object] = {}


def check(engine: str) -> None:
    if engine == "chatterbox":
        from chatterbox.tts import ChatterboxTTS  # noqa: F401
    elif engine == "kokoro":
        import kokoro_mlx  # noqa: F401
    else:
        raise ValueError(f"Unknown worker engine {engine}")


def chatterbox(payload: dict) -> None:
    import torch
    import soundfile as sf
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine", nargs="?")
    parser.add_argument("--check")
    args = parser.parse_args()
    if args.check:
        check(args.check)
        return
    handlers = {"chatterbox": chatterbox, "kokoro": kokoro}
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
