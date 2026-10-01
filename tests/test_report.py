import json

from nerfwatch.report import compare, item_pass, summarise, table


def _write(path, passes):
    with open(path, "w") as f:
        for i, p in enumerate(passes):
            for t in (0.0, 0.7):
                f.write(json.dumps({"id": f"x-{i}", "family": "fact", "temperature": t, "sample": 0, "output": "", "pass": p, "latency_s": 0}) + "\n")


def test_summarise_and_compare(tmp_path):
    a, b = tmp_path / "r1.jsonl", tmp_path / "r2.jsonl"
    _write(a, [True] * 8 + [False] * 2)
    _write(b, [True] * 5 + [False] * 5)
    assert summarise(a)["k"] == 8 and summarise(b)["n"] == 10
    assert item_pass(a)["x-9"] is False
    c = compare(a, b)
    assert abs(c["diff"] + 0.3) < 1e-9 and c["b_to_fail"] == 3 and c["c_to_pass"] == 0
    assert "r1" in table(tmp_path)
