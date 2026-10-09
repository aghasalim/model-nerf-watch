"""Small-sample statistics for pass rates. Standard library only."""

import math
from statistics import NormalDist

_N = NormalDist()


def wilson(k, n, conf=0.95):
    """Wilson score interval for a binomial proportion. Returns (p, lo, hi)."""
    if n == 0:
        return 0.0, 0.0, 1.0
    z = _N.inv_cdf(1 - (1 - conf) / 2)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo, hi = centre - half, centre + half
    return p, 0.0 if lo < 1e-12 else lo, 1.0 if hi > 1 - 1e-12 else hi


def diff_ci(k1, n1, k2, n2, conf=0.95):
    """Newcombe hybrid score interval for p2 - p1. Returns (diff, lo, hi)."""
    p1, l1, u1 = wilson(k1, n1, conf)
    p2, l2, u2 = wilson(k2, n2, conf)
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return d, lo, hi


def two_proportion_test(k1, n1, k2, n2):
    """Pooled two-proportion z-test, two-sided. Returns (z, p_value).

    An empty group carries no evidence, so it returns (0.0, 1.0) rather than
    dividing by zero.
    """
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (k2 / n2 - k1 / n1) / se
    return z, 2 * (1 - _N.cdf(abs(z)))


def mcnemar(b, c):
    """Exact McNemar test on the discordant counts.

    b: items that passed before and fail now. c: items that failed before and
    pass now. Returns the two-sided exact binomial p-value.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def probes_needed(p_before, drop, alpha=0.05, power=0.8):
    """Items per run needed for a two-proportion test to detect a drop of
    `drop` (in proportion units) from `p_before`, two-sided alpha, given power."""
    p2 = p_before - drop
    if not 0 < p2 < 1 or not 0 < p_before <= 1:
        raise ValueError("drop must leave the pass rate inside (0, 1)")
    za = _N.inv_cdf(1 - alpha / 2)
    zb = _N.inv_cdf(power)
    pbar = (p_before + p2) / 2
    num = za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p_before * (1 - p_before) + p2 * (1 - p2))
    return math.ceil((num / drop) ** 2)


def paired_counts(before, after):
    """before/after: dict item -> bool. Returns (b, c) discordant counts."""
    keys = before.keys() & after.keys()
    b = sum(before[k] and not after[k] for k in keys)
    c = sum(not before[k] and after[k] for k in keys)
    return b, c
