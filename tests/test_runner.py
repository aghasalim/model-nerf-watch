import pytest

from nerfwatch import runner


def test_resume_refuses_a_different_max_tokens(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "RESULTS", tmp_path)
    monkeypatch.setattr(runner, "complete", lambda *a, **k: "x")
    runner.run("m", n=1, temperatures=(0.0,), run_name="r", max_tokens=256, log=lambda *_: None)
    # Same budget resumes with nothing left to do.
    runner.run("m", n=1, temperatures=(0.0,), run_name="r", max_tokens=256, log=lambda *_: None)
    with pytest.raises(ValueError, match="max_tokens"):
        runner.run("m", n=2, temperatures=(0.0,), run_name="r", max_tokens=1024, log=lambda *_: None)
