from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


class JsonWorker:
    def __init__(self, engine: str):
        self.engine = engine
        self.process: subprocess.Popen[str] | None = None
        self.lock = threading.Lock()
        self.jobs = 0
        self.last_response: dict[str, Any] = {}

    def available(self) -> tuple[bool, str | None]:
        python = self._python()
        if not Path(python).exists():
            return False, f"Configured {self.engine} runtime does not exist: {python}"
        command = [python, "-m", "shadowlearn.engine_worker", "--check", self.engine]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, env=self._environment())
        if result.returncode == 0:
            return True, None
        lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
        reason = lines[-1] if lines else f"{self.engine} runtime check failed"
        if reason.startswith("ModuleNotFoundError:"):
            reason = f"{self.engine} is not installed ({reason.partition(':')[2].strip()})"
        return False, reason

    def request(self, payload: dict[str, Any], timeout: float = 1800) -> dict[str, Any]:
        with self.lock:
            if not self.process or self.process.poll() is not None or self.jobs >= 20:
                self.close()
                env = self._environment()
                self.process = subprocess.Popen(
                    [self._python(), "-m", "shadowlearn.engine_worker", self.engine],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    env=env,
                )
                self.jobs = 0
            assert self.process.stdin and self.process.stdout
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
            ready, _, _ = select.select([self.process.stdout], [], [], timeout)
            if not ready:
                self.close()
                raise TimeoutError(f"{self.engine} worker timed out")
            line = self.process.stdout.readline()
            if not line:
                error = self.process.stderr.read() if self.process.stderr else "worker exited"
                self.close()
                raise RuntimeError(error.strip())
            self.jobs += 1
            response = json.loads(line)
            self.last_response = response
            if not response.get("ok"):
                detail = response.get("trace") or response.get("error", "engine failed")
                raise RuntimeError(detail)
            return response

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def _python(self) -> str:
        variable = f"SHADOW_LEARN_{self.engine.upper()}_PYTHON"
        return os.environ.get(variable, sys.executable)

    def _environment(self) -> dict[str, str]:
        env = dict(os.environ)
        backend = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = backend + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        env["TOKENIZERS_PARALLELISM"] = "false"
        return env
