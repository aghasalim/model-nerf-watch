"""Markdown table and figures from the results directory."""

import json
from collections import defaultdict
from pathlib import Path

from .runner import RESULTS, load_results
from .stats import diff_ci, mcnemar, paired_counts, two_proportion_test, wilson


def runs_for(model_dir):
    return sorted(Path(model_dir).glob("*.jsonl"))


def summarise(path, temperature=0.0):
    """Pass counts for one run at one temperature, overall and per family."""
    rows = [r for r in load_results(path) if r["temperature"] == temperature]
    fam = defaultdict(lambda: [0, 0])
    for r in rows:
        fam[r["family"]][0] += r["pass"]
        fam[r["family"]][1] += 1
    k, n = sum(r["pass"] for r in rows), len(rows)
    return {"run": path.stem, "k": k, "n": n, "families": dict(fam)}


def item_pass(path, temperature=0.0):
    """Majority vote per probe id, so paired tests compare one item to itself."""
    votes = defaultdict(list)
    for r in load_results(path):
        if r["temperature"] == temperature:
            votes[r["id"]].append(r["pass"])
    return {k: sum(v) > len(v) / 2 for k, v in votes.items()}


def compare(path_a, path_b, temperature=0.0):
    a, b = summarise(path_a, temperature), summarise(path_b, temperature)
    d, lo, hi = diff_ci(a["k"], a["n"], b["k"], b["n"])
    z, p_z = two_proportion_test(a["k"], a["n"], b["k"], b["n"])
    disc_b, disc_c = paired_counts(item_pass(path_a, temperature), item_pass(path_b, temperature))
    return {"a": a["run"], "b": b["run"], "diff": d, "lo": lo, "hi": hi, "z": z, "p_z": p_z,
            "b_to_fail": disc_b, "c_to_pass": disc_c, "p_mcnemar": mcnemar(disc_b, disc_c)}


def table(model_dir, temperature=0.0):
    lines = ["| run | pass | n | rate | 95% CI |", "|---|---|---|---|---|"]
    for path in runs_for(model_dir):
        s = summarise(path, temperature)
        p, lo, hi = wilson(s["k"], s["n"])
        lines.append(f"| {s['run']} | {s['k']} | {s['n']} | {p:.3f} | {lo:.3f} to {hi:.3f} |")
    return "\n".join(lines)


def drift_figure(model_dirs, out, temperature=0.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    labels = []
    for d in model_dirs:
        runs = runs_for(d)
        pts = [wilson(s["k"], s["n"]) for s in (summarise(r, temperature) for r in runs)]
        x = range(len(labels), len(labels) + len(runs))
        labels += [f"{Path(d).name}\n{r.stem}" for r in runs]
        ax.plot(x, [p for p, _, _ in pts], marker="o", label=Path(d).name)
        ax.fill_between(x, [lo for _, lo, _ in pts], [hi for _, _, hi in pts], alpha=0.2)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel(f"pass rate at temperature {temperature}")
    ax.set_ylim(0, 1.02)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)


def noise_floor_figure(model_dir, out, temperature=0.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    runs = runs_for(model_dir)
    cmps = [compare(runs[i], runs[i + 1], temperature) for i in range(len(runs) - 1)]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    for i, c in enumerate(cmps):
        ax.errorbar(i, c["diff"], yerr=[[c["diff"] - c["lo"]], [c["hi"] - c["diff"]]], fmt="o", capsize=4, color="C0")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xticks(range(len(cmps)))
    ax.set_xticklabels([f"{c['a']}\nvs {c['b']}" for c in cmps], fontsize=8)
    ax.set_ylabel("pass rate difference (95% CI)")
    ax.set_title(f"{Path(model_dir).name}: same model, consecutive runs")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    return cmps


def family_figure(model_dirs, out, temperature=0.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.8 / len(model_dirs)
    fams = ["arithmetic", "string", "code", "fact"]
    for j, d in enumerate(model_dirs):
        agg = defaultdict(lambda: [0, 0])
        for r in runs_for(d):
            for fam, (k, n) in summarise(r, temperature)["families"].items():
                agg[fam][0] += k
                agg[fam][1] += n
        pts = [wilson(*agg[f]) for f in fams]
        xs = [i + j * width for i in range(len(fams))]
        ax.bar(xs, [p for p, _, _ in pts], width, label=Path(d).name,
               yerr=[[p - lo for p, lo, _ in pts], [hi - p for p, _, hi in pts]], capsize=3)
    ax.set_xticks([i + width * (len(model_dirs) - 1) / 2 for i in range(len(fams))])
    ax.set_xticklabels(fams)
    ax.set_ylabel("pass rate, all runs pooled")
    ax.set_ylim(0, 1.05)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)


def write_summary(model_dirs, out_json, temperature=0.0):
    """Every number the README quotes comes from this file."""
    summary = {}
    for d in model_dirs:
        runs = runs_for(d)
        summary[Path(d).name] = {
            "runs": [dict(summarise(r, temperature), ci=wilson(*[summarise(r, temperature)[k] for k in ("k", "n")])) for r in runs],
            "runs_t07": [summarise(r, 0.7) for r in runs],
            "consecutive": [compare(runs[i], runs[i + 1], temperature) for i in range(len(runs) - 1)],
        }
    names = list(summary)
    if len(names) > 1:
        base = runs_for(model_dirs[0])[-1]
        summary["cross"] = [compare(base, r, temperature) for r in runs_for(model_dirs[1])]
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=1)
    return summary
