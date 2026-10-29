"""Optional local-only llama.cpp process lifecycle, never a paid API fallback."""
from __future__ import annotations
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from .util import ROOT

def healthy(url="http://127.0.0.1:8080/health"):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

@contextmanager
def local_director(backend="auto"):
    """Use an existing endpoint or temporarily start our installed CPU server.

    Only explicit `llama` starts the local model. Default auto uses Codex; the
    main session workflow uses the active conversation without nested inference.
    A foreign endpoint is never silently selected.
    """
    if backend != "llama" or os.environ.get("MINESTORY_LLM_URL") or healthy():
        yield
        return
    binary = ROOT/".tools/llama/llama-b11982/llama-server"
    model = ROOT/".models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    if not binary.exists() or not model.exists():
        if backend == "llama":
            raise RuntimeError("Diretor local ausente. Execute .venv/bin/python scripts/bootstrap.py --local-director")
        yield
        return
    cache = ROOT/".cache"
    cache.mkdir(exist_ok=True)
    with (cache/"llm-server.log").open("a") as log:
        process = subprocess.Popen([str(binary),"--model",str(model),"--host","127.0.0.1","--port","8080",
                                    "--ctx-size","8192","--threads",str(min(os.cpu_count() or 2,3)),
                                    "--threads-batch",str(min(os.cpu_count() or 2,3)),"--n-gpu-layers","0",
                                    "--parallel","1","--log-disable"],stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+45
            while not healthy():
                if process.poll() is not None:
                    raise RuntimeError("llama-server terminou durante a carga; consulte .cache/llm-server.log")
                if time.monotonic()>deadline:
                    raise TimeoutError("Diretor local não ficou pronto em 45s; consulte .cache/llm-server.log")
                time.sleep(.2)
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
