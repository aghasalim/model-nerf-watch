"""Re-derive every number quoted in README.md from results/ and fail on mismatch.

The README refers to numbers with a `<!-- num:KEY -->VALUE` marker. This script
rebuilds summary.json from the raw jsonl, looks every KEY up, and compares.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nerfwatch.report import RESULTS, write_summary  # noqa: E402

BASE = "ollama_qwen3_8b"
PLANT = "ollama_qwen3_4b"


def derive():
    dirs = [RESULTS / BASE, RESULTS / PLANT]
    s = write_summary([d for d in dirs if d.exists()], RESULTS / "summary.json")
    out = {}
    for name, m in s.items():
        if name == "cross":
            continue
        for i, r in enumerate(m["runs"], 1):
            out[f"{name}.r{i}.k"] = r["k"]
            out[f"{name}.r{i}.n"] = r["n"]
            out[f"{name}.r{i}.rate"] = f"{r['ci'][0]:.3f}"
            out[f"{name}.r{i}.lo"] = f"{r['ci'][1]:.3f}"
            out[f"{name}.r{i}.hi"] = f"{r['ci'][2]:.3f}"
            for fam, (k, n) in r["families"].items():
                out[f"{name}.r{i}.{fam}"] = f"{k}/{n}"
        for i, r in enumerate(m["runs_t07"], 1):
            out[f"{name}.r{i}.t07.k"] = r["k"]
            out[f"{name}.r{i}.t07.n"] = r["n"]
        for i, c in enumerate(m["consecutive"], 1):
            out[f"{name}.c{i}.diff"] = f"{c['diff']:+.3f}"
            out[f"{name}.c{i}.lo"] = f"{c['lo']:+.3f}"
            out[f"{name}.c{i}.hi"] = f"{c['hi']:+.3f}"
            out[f"{name}.c{i}.p_z"] = f"{c['p_z']:.2f}"
            out[f"{name}.c{i}.p_mcnemar"] = f"{c['p_mcnemar']:.2f}"
            out[f"{name}.c{i}.b"] = c["b_to_fail"]
            out[f"{name}.c{i}.c"] = c["c_to_pass"]
    for i, c in enumerate(s.get("cross", []), 1):
        out[f"cross{i}.diff"] = f"{c['diff']:+.3f}"
        out[f"cross{i}.lo"] = f"{c['lo']:+.3f}"
        out[f"cross{i}.hi"] = f"{c['hi']:+.3f}"
        out[f"cross{i}.p_z"] = f"{c['p_z']:.1e}"
        out[f"cross{i}.p_mcnemar"] = f"{c['p_mcnemar']:.1e}"
        out[f"cross{i}.b"] = c["b_to_fail"]
        out[f"cross{i}.c"] = c["c_to_pass"]
    from nerfwatch.stats import probes_needed
    for drop in (5, 10, 20):
        out[f"power.drop{drop}"] = probes_needed(0.9, drop / 100)
    return out


def main():
    readme = (ROOT / "README.md").read_text()
    quoted = re.findall(r"<!-- num:([\w.]+) -->([^<\s|,.)]+(?:\.\d+)?(?:e[+-]\d+)?)", readme)
    if not quoted:
        sys.exit("README quotes no marked numbers")
    derived = derive()
    bad = [(k, v, derived.get(k)) for k, v in quoted if str(derived.get(k)) != v]
    for k, v, d in bad:
        print(f"MISMATCH {k}: README says {v}, results say {d}")
    print(f"checked {len(quoted)} quoted numbers, {len(bad)} mismatches")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
