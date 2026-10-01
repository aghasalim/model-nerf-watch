import math

import pytest

from nerfwatch.stats import diff_ci, mcnemar, paired_counts, probes_needed, two_proportion_test, wilson


def test_wilson_known_values():
    # Brown, Cai, DasGupta style check: 50/60, z=1.96
    p, lo, hi = wilson(50, 60)
    assert p == pytest.approx(0.8333, abs=1e-4)
    assert lo == pytest.approx(0.7197, abs=1e-3)
    assert hi == pytest.approx(0.9069, abs=1e-3)


def test_wilson_edges():
    assert wilson(0, 0) == (0.0, 0.0, 1.0)
    p, lo, hi = wilson(10, 10)
    assert p == 1.0 and hi == 1.0 and lo == pytest.approx(0.7225, abs=1e-3)
    assert wilson(0, 10)[1] == 0.0


def test_two_proportion_known_value():
    # 50/100 vs 40/100: pooled p=0.45, se=0.07036, z=1.4213
    z, p = two_proportion_test(50, 100, 40, 100)
    assert z == pytest.approx(-1.4213, abs=1e-3)
    assert p == pytest.approx(0.1552, abs=1e-3)


def test_two_proportion_identical_is_one():
    assert two_proportion_test(60, 60, 60, 60) == (0.0, 1.0)


def test_mcnemar_exact():
    assert mcnemar(0, 0) == 1.0
    assert mcnemar(5, 5) == 1.0
    # b=6, c=0: P(X<=0 | n=6) * 2 = 2/64
    assert mcnemar(6, 0) == pytest.approx(2 / 64)
    assert mcnemar(1, 0) == 1.0


def test_paired_counts():
    before = {"a": True, "b": True, "c": False, "d": False}
    after = {"a": True, "b": False, "c": True, "d": False, "e": True}
    assert paired_counts(before, after) == (1, 1)


def test_diff_ci_contains_point_and_zero_for_same_data():
    d, lo, hi = diff_ci(50, 60, 50, 60)
    assert d == 0 and lo < 0 < hi
    p, l, u = 0.8333, 0.7197, 0.9069
    assert hi - lo == pytest.approx(2 * math.sqrt((p - l) ** 2 + (u - p) ** 2), abs=2e-3)


def test_probes_needed_textbook():
    # Standard result: 0.5 vs 0.6, alpha 0.05 two-sided, power 0.8 -> about 388 per group
    assert probes_needed(0.6, 0.1) == pytest.approx(388, abs=3)
    assert probes_needed(0.9, 0.1) < probes_needed(0.6, 0.1)
    with pytest.raises(ValueError):
        probes_needed(0.5, 0.5)
