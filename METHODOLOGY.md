# Methodology

Rules this repo follows. If a change breaks one of them, the change is wrong.

## Every number is measured

Every number in README.md is derived from a file under `results/`. Each one is
tagged with a `<!-- num:KEY -->` marker and `scripts/check_numbers.py`
recomputes it from the raw jsonl in CI. If the README and the data disagree,
CI goes red. There are no illustrative numbers, no numbers from memory.

## Negatives stay

Runs that found nothing, probes the model never gets right, and comparisons
that are not significant all stay in the results and in the logbook. The
noise floor (the difference between two runs of the same model) is the most
important result here and it is reported before any "detected" drop.

## No LLM judges

Every probe has a programmatic check: exact string, number match, a hidden
test for code, or a normalised fact string. A judge model would add a second
moving part that could itself degrade, which defeats the purpose.

## Variance is part of the result

Each probe is sampled `n` times at temperature 0 and again at temperature
0.7. The temperature 0 samples are the canary. The temperature 0.7 samples
show how much the model moves on its own. Pass rates always come with a
Wilson 95% interval, never bare.

## Two tests, both reported

Between two runs the repo reports a pooled two-proportion z-test and an exact
McNemar test on the per-item majority vote. The z-test treats samples as
independent, which they are not quite (three samples of the same item are
correlated). McNemar pairs each item with itself and only looks at items that
flipped. When they disagree, McNemar is the one to trust for "did the same
model change", and the z-test is the one that matches most dashboards.

## Power is stated up front

`nerfwatch power --baseline 0.9 --drop 0.1` prints how many probes a run needs
before a drop of that size is detectable at alpha 0.05 and power 0.8. The
README states what the current probe set can and cannot see.

## Planted degradation is labelled

The only "nerf" in this repo is planted: a smaller quantised sibling of the
same model family, run through the same pipeline. It is labelled as planted
wherever it appears. Nothing here claims a real provider silently changed a
model.

## CI guards

`pytest` covers the statistics with known-answer tests, the scorer, and every
provider adapter against recorded fixtures. `check_numbers.py` guards the
README. `check_style.py` rejects em and en dashes so the prose stays plain.
