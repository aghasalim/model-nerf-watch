from nerfwatch.probes import load_probes, score

P = {p["id"]: p for p in load_probes()}


def test_sixty_probes_four_families():
    fams = {p["family"] for p in P.values()}
    assert len(P) == 60 and fams == {"arithmetic", "string", "code", "fact"}


def test_arithmetic_takes_last_number_and_strips_think():
    assert score(P["arith-01"], "<think>hmm</think>\nThe answer is 3,901.")
    assert score(P["arith-01"], "hmm 3800... no.\n</think>\n\n3901")
    assert score(P["arith-01"], "3901")
    assert not score(P["arith-01"], "3900")
    assert not score(P["arith-01"], "no idea")


def test_string_is_exact():
    assert score(P["str-01"], "ananab\n")
    assert not score(P["str-01"], "'ananab'")
    assert not score(P["str-01"], "Ananab")


def test_fact_is_case_and_punctuation_insensitive():
    assert score(P["fact-01"], "canberra.")
    assert score(P["fact-05"], "the pacific ocean".title())
    assert not score(P["fact-01"], "Sydney")
    assert score(P["fact-14"], "H\u2082O")


def test_code_runs_hidden_tests():
    assert score(P["code-01"], "```python\ndef add(a, b):\n    return a + b\n```")
    assert not score(P["code-01"], "def add(a, b):\n    return a - b")
    assert not score(P["code-01"], "def plus(a, b):\n    return a + b")
    assert not score(P["code-01"], "this is not python")


def test_code_infinite_loop_times_out():
    assert not score(P["code-01"], "def add(a, b):\n    while True: pass")


def test_reference_answers_pass_their_own_scorer():
    for p in P.values():
        if p["family"] != "code":
            assert score(p, str(p["answer"])), p["id"]
