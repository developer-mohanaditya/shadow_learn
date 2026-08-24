from __future__ import annotations

import argparse
import json
import resource
import statistics
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .config import settings
from .database import db
from .engines import registry
from .audio import duration


WEIGHTS = {
    "naturalness": 0.30,
    "pronunciation": 0.25,
    "prosody": 0.20,
    "punctuation": 0.15,
    "clone_similarity": 0.10,
}


def benchmark(engine_id: str, repeat: int = 1, corpus_path: Path | None = None) -> dict:
    corpus_path = corpus_path or settings.root / "benchmark" / "corpus.json"
    corpus = json.loads(corpus_path.read_text())
    engine = registry.get(engine_id)
    health = engine.health()
    if not health.available:
        raise RuntimeError(health.reason or f"{engine_id} unavailable")
    run_id = str(uuid4())
    output = settings.data / "benchmarks" / run_id
    output.mkdir(parents=True, exist_ok=True)
    samples = []
    failures = []
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    worker_peak = 0
    for iteration in range(repeat):
        for item in corpus:
            target = output / f"{iteration:02d}-{item['id']}.wav"
            started = time.perf_counter()
            try:
                engine.synthesize(
                    item["text"], target, None,
                    {"accent": item["accent"], "pace": 1, "mood": "neutral", "expressiveness": .5},
                    threading.Event(),
                )
                worker = getattr(engine, "worker", None)
                if worker:
                    worker_peak = max(worker_peak, int(worker.last_response.get("peak_rss_bytes", 0)))
                elapsed = time.perf_counter() - started
                audio_seconds = duration(target)
                samples.append({
                    "id": item["id"], "iteration": iteration, "generation_seconds": elapsed,
                    "audio_seconds": audio_seconds, "rtf": elapsed / audio_seconds, "path": str(target),
                })
            except Exception as exc:
                failures.append({"id": item["id"], "iteration": iteration, "error": str(exc)})
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    metrics = {
        "engine": engine_id,
        "samples": samples,
        "failures": failures,
        "average_rtf": statistics.mean(sample["rtf"] for sample in samples) if samples else None,
        "peak_rss_bytes": max(before, after, worker_peak),
        "completed": len(samples),
        "expected": len(corpus) * repeat,
        "manual_scores": None,
    }
    db.initialize()
    db.execute(
        "INSERT INTO benchmark_runs(id,engine,metrics_json,score,qualifies,created_at) VALUES (?,?,?,NULL,0,?)",
        (run_id, engine_id, json.dumps(metrics), datetime.now(UTC).isoformat()),
    )
    (output / "result.json").write_text(json.dumps({"run_id": run_id, **metrics}, indent=2))
    return {"run_id": run_id, **metrics}


def score(run_id: str, scores: dict[str, float]) -> dict:
    missing = set(WEIGHTS) - set(scores)
    if missing:
        raise ValueError(f"Missing scores: {', '.join(sorted(missing))}")
    if any(not 1 <= float(value) <= 5 for value in scores.values()):
        raise ValueError("Every listening score must be between 1 and 5")
    row = db.fetch_one("SELECT * FROM benchmark_runs WHERE id=?", (run_id,))
    if not row:
        raise ValueError("Benchmark run not found")
    metrics = json.loads(row["metrics_json"])
    weighted = sum(float(scores[key]) * weight for key, weight in WEIGHTS.items())
    technical = not metrics["failures"] and metrics["average_rtf"] is not None and metrics["average_rtf"] <= 1
    metrics["manual_scores"] = scores
    db.execute(
        "UPDATE benchmark_runs SET metrics_json=?,score=?,qualifies=? WHERE id=?",
        (json.dumps(metrics), weighted, int(technical), run_id),
    )
    return {"run_id": run_id, "weighted_score": weighted, "technical_gate": technical}


def run() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Shadow Learn speech engines")
    sub = parser.add_subparsers(dest="command", required=True)
    execute = sub.add_parser("run")
    execute.add_argument("engine", choices=["chatterbox", "zonos2", "kokoro", "system"])
    execute.add_argument("--repeat", type=int, default=1)
    listening = sub.add_parser("score")
    listening.add_argument("run_id")
    for key in WEIGHTS:
        listening.add_argument(f"--{key.replace('_', '-')}", type=float, required=True)
    args = parser.parse_args()
    if args.command == "run":
        result = benchmark(args.engine, args.repeat)
    else:
        scores = {key: getattr(args, key) for key in WEIGHTS}
        result = score(args.run_id, scores)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
