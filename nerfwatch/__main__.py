import argparse
import json
from pathlib import Path

from .report import RESULTS, compare, drift_figure, family_figure, noise_floor_figure, table, write_summary
from .runner import rescore, run
from .stats import probes_needed


def main():
    ap = argparse.ArgumentParser(prog="nerfwatch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="sample every probe against a model")
    r.add_argument("--model", required=True, help="provider/model, e.g. ollama/qwen3:8b")
    r.add_argument("--n", type=int, default=3)
    r.add_argument("--temps", default="0,0.7")
    r.add_argument("--run-name", default=None, help="defaults to today's date")
    r.add_argument("--max-tokens", type=int, default=256)
    rp = sub.add_parser("report", help="tables, figures and summary.json")
    rp.add_argument("--models", nargs="*", help="result dirs, defaults to all")
    c = sub.add_parser("compare", help="two result files")
    c.add_argument("a")
    c.add_argument("b")
    rs = sub.add_parser("rescore", help="re-score stored outputs after a scorer change")
    rs.add_argument("files", nargs="+")
    p = sub.add_parser("power", help="how many probes to detect a drop")
    p.add_argument("--baseline", type=float, required=True)
    p.add_argument("--drop", type=float, required=True)
    p.add_argument("--power", type=float, default=0.8)
    a = ap.parse_args()

    if a.cmd == "run":
        run(a.model, a.n, tuple(float(t) for t in a.temps.split(",")), a.run_name, a.max_tokens)
    elif a.cmd == "report":
        dirs = [RESULTS / m for m in a.models] if a.models else sorted((d for d in RESULTS.iterdir() if d.is_dir()), key=lambda d: -len(list(d.glob('*.jsonl'))))
        for d in dirs:
            print(f"\n### {d.name}\n\n{table(d)}")
        drift_figure(dirs, RESULTS / "drift.png")
        family_figure(dirs, RESULTS / "families.png")
        noise_floor_figure(dirs[0], RESULTS / "noise-floor.png")
        write_summary(dirs, RESULTS / "summary.json")
    elif a.cmd == "compare":
        print(json.dumps(compare(Path(a.a), Path(a.b)), indent=1))
    elif a.cmd == "rescore":
        for f in a.files:
            rescore(Path(f))
    elif a.cmd == "power":
        print(probes_needed(a.baseline, a.drop, power=a.power))


if __name__ == "__main__":
    main()
