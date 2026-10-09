# Logbook

## 2026-10-01

Started the project. The itch comes from a Hacker News thread where people
kept saying the models they pay for feel worse than last month and nobody
had numbers. One comment put it well: "it's so easy to check, but nobody
ever proves it." So: check it, and be honest about how much a check can see.

Decisions made today:

- Plain `urllib` adapters, no SDKs. Six providers behind one `provider/model`
  string. Only Ollama is reachable on this machine, the rest get recorded
  fixtures and request-shape tests.
- 60 probes, 15 per family. Every answer is checked by code. For the code
  family the model's function runs against hidden tests under a 2 second
  alarm.
- qwen3 thinks by default. With thinking on, a 64 token budget gets eaten by
  the `<think>` block and the answer never arrives. `think: false` in the
  Ollama chat API turns it off. Documented in the README.
- Each probe sampled 3 times at temperature 0 and 3 times at 0.7, with
  `seed` set to the sample index so a rerun is reproducible as far as the
  backend allows.

Timings: a warm short answer from qwen3:8b on this M4 takes about 1 second,
the first call after load about 6. A full run (60 probes, 2 temperatures,
3 samples) is around 10 to 15 minutes.

Things that went wrong:

- The first version of the fact scorer failed "The Pacific Ocean" against
  "Pacific Ocean". Leading articles are now stripped. This was caught by the
  test, not by the run.
- My own expectation for the width of the Newcombe interval was wrong in a
  test (I had used a symmetric formula). The code was right, the test was
  not. Fixed the test after working the formula through by hand.
- `ollama list` shows `qwen3:8b` and a `gemma-4-31b-it-qat` tag sharing the
  same blob id on this machine, so that tag is just an alias of qwen3:8b,
  not a 31B model. Not used here, noted so nobody is surprised.
- Pulling `qwen3:4b` for the planted degradation ran at about 1 MB/s and
  took half an hour. Nothing to fix, just slow.

Early observations from the first run, before any statistics: the model is
confidently wrong on 47 * 83 (says 3801) and on 1001 mod 7 (says 2), at both
temperatures, all three samples. Those are stable failures, not noise, which
is the kind of item that makes a paired test useful.

Later the same day, the first real result and a mistake.

After three runs the pass rate was identical to the item: 162 of 180 at
temperature 0 and 160 of 180 at temperature 0.7, three times over. At 0.7
that is suspicious. The cause was my own `seed`: I had set it to the sample
index for every call, so Ollama replayed the same random draws in every run.
178 of 180 temperature 0 outputs and 180 of 180 temperature 0.7 outputs were
byte identical across runs. That is a useful fact about local Ollama (fix
the seed and the run is reproducible), but it is not a noise floor, because
a hosted API will not let you do that.

Fix: the seed is only set at temperature 0 now. I deleted the temperature
0.7 rows from the three result files and let the resumable runner fill them
back in with unseeded sampling. The temperature 0 rows were kept as they
were.

Also changed the fact scorer to NFKC-normalise unicode, because the model
writes H₂O with a subscript and that is a correct answer. Stored outputs
were re-scored with `nerfwatch rescore` so all runs use the same scorer.
Left as is: "Japanese Yen (JPY)" fails against "Yen". That is a probe
wording defect, not a model error, and it stays in the data as a known one.

The planted degradation is `qwen3:4b`, the same family, same quantisation
type, half the parameters. It is run through the same pipeline and labelled
as planted everywhere it appears.

Planted run, evening. `qwen3:4b` scored 14 of 180 on the first pass. Too
low to be a capability story, so I read the outputs: the model was thinking
in plain prose, ignoring `think: false`, and the 256 token budget ran out
before any answer. Ollama also strips the opening `<think>` tag from the
content, so my scorer's `<think>...</think>` regex never matched and the
answer after `</think>` was never isolated. Two changes: the scorer now cuts
everything up to the last `</think>`, and `run` has `--max-tokens`. After
re-scoring, the 256 budget run sits at 62 of 180. A second run at 1024
tokens gives 117 of 180, about 16 seconds per call instead of 0.3.

Both planted runs stay in `results/`. The first one is the more useful: it
is what a format regression looks like to a canary, and it is
indistinguishable from a capability drop until you open the raw outputs.

Also deleted a 10 line partial file from an interrupted earlier start of the
planted run. The runner is resumable so it would have continued, but the
run name was wrong.

## 2026-10-10

`two_proportion_test(0, 0, 0, 0)` raised ZeroDivisionError, and so did any
call with one empty group. An empty group carries no evidence, so it now
returns z = 0 and p = 1, the same answer as two identical groups. No
published number moves.

`run` resumed by (id, temperature, sample) and ignored the token budget, so
rerunning a run name with a different `--max-tokens` would have filled the
rest of the file at the new budget and mixed the two. It now refuses with a
ValueError when the file already holds rows recorded at another budget. The
oldest files have no `max_tokens` field and still resume as before.
