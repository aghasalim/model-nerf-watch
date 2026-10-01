"""Probe loading and programmatic scoring. No LLM judge anywhere."""

import json
import re
import signal
import unicodedata
from pathlib import Path

PROBE_DIR = Path(__file__).resolve().parent.parent / "probes"


def load_probes(probe_dir=PROBE_DIR):
    probes = []
    for path in sorted(Path(probe_dir).glob("*.jsonl")):
        with open(path) as f:
            probes += [json.loads(line) for line in f if line.strip()]
    ids = [p["id"] for p in probes]
    assert len(ids) == len(set(ids)), "duplicate probe ids"
    return probes


def _strip(text):
    # Ollama strips the opening <think> tag, so cut everything up to the last closing one.
    text = text.rsplit("</think>", 1)[-1]
    text = re.sub(r"```[a-zA-Z]*\n?|```", "", text)
    return text.strip()


def _norm(text):
    text = unicodedata.normalize("NFKC", text)  # H₂O -> H2O
    text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return re.sub(r"^(the|a|an) ", "", text)


def _last_number(text):
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return nums[-1] if nums else None


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout


def _run_code(src, probe):
    """Run the model's function against the hidden tests. Any failure is a fail.

    The code runs in-process with a 2 second alarm. It is model output, so run
    the benchmark on a machine you do not mind the model touching.
    """
    ns = {}
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(2)  # ponytail: alarm is main-thread only, use a subprocess if this is ever threaded
    try:
        exec(src, ns)  # noqa: S102, deliberate, this is what a code probe is
        fn = ns[probe["function"]]
        return all(fn(*args) == expected for args, expected in probe["tests"])
    except BaseException:
        return False
    finally:
        signal.alarm(0)


def score(probe, output):
    out = _strip(output)
    family = probe["family"]
    if family == "arithmetic":
        got = _last_number(out)
        return got is not None and float(got) == float(probe["answer"])
    if family == "string":
        return out == probe["answer"]
    if family == "fact":
        return _norm(out) == _norm(probe["answer"])
    if family == "code":
        return _run_code(out, probe)
    raise ValueError(family)
