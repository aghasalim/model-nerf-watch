"""Run the probe set against a model and append per-item results. Resumable."""

import datetime as dt
import json
import time
from pathlib import Path

from .probes import load_probes, score
from .providers import complete

RESULTS = Path(__file__).resolve().parent.parent / "results"


def result_path(model, run_name):
    return RESULTS / model.replace("/", "_").replace(":", "_") / f"{run_name}.jsonl"


def load_results(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def run(model, n=3, temperatures=(0.0, 0.7), run_name=None, max_tokens=256, log=print):
    """Sample every probe `n` times at each temperature and append to the run's jsonl.

    Items already present in the file are skipped, so an interrupted run can be
    restarted with the same `run_name` and it picks up where it stopped.
    Returns the path of the jsonl file.
    """
    path = result_path(model, run_name or dt.date.today().isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = load_results(path) if path.exists() else []
    # Resuming under a different token budget would mix two budgets in one run.
    # Older rows have no max_tokens field, so only a recorded mismatch counts.
    other = {r["max_tokens"] for r in rows if r.get("max_tokens") not in (None, max_tokens)}
    if other:
        raise ValueError(f"{path} was run with max_tokens={sorted(other)}, not {max_tokens}; use a new run name")
    done = {(r["id"], r["temperature"], r["sample"]) for r in rows}
    probes = load_probes()
    todo = [(p, t, s) for p in probes for t in temperatures for s in range(n) if (p["id"], t, s) not in done]
    log(f"{model}: {len(done)} done, {len(todo)} to go -> {path}")
    with open(path, "a") as f:
        for i, (p, t, s) in enumerate(todo, 1):
            t0 = time.time()
            out = complete(model, p["prompt"], temperature=t, seed=s, max_tokens=max_tokens)
            rec = {"id": p["id"], "family": p["family"], "temperature": t, "sample": s,
                   "output": out, "pass": score(p, out), "max_tokens": max_tokens, "latency_s": round(time.time() - t0, 3)}
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if i % 20 == 0:
                log(f"  {i}/{len(todo)}")
    return path


def rescore(path):
    """Re-run the scorer over stored outputs, for when the scorer changes."""
    probes = {p["id"]: p for p in load_probes()}
    rows = load_results(path)
    for r in rows:
        r["pass"] = score(probes[r["id"]], r["output"])
    with open(path, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
