# bb_agents
bridge bidding agents

Python 3.14 project (managed with `uv`) for training bridge bidding agents. So far it contains a **deal sampler**: it generates random bridge deals and analyzes them with the DDS double-dummy solver (tricks per strain and declarer, plus par score and contract).

## Quick start

```bash
make install   # build DDS wheel + uv sync (see "Building DDS" below)
make test      # run the pytest suite
make sample    # print a random deal with its double-dummy analysis
make sample SEED=42   # same, but reproducible
```

## Using the sampler

```python
from consts import Vulnerability
from sampler import DealSampler

sampler = DealSampler(seed=42)  # seed is optional
deal, analysis = sampler.sample_and_analyze(Vulnerability.NONE)
print(DealSampler.format_report(deal, analysis))
```

The report contains the PBN string, the hands per seat, a strain-by-seat table of double-dummy tricks, and the par score and contract. `sample_deal()`, `analyze()`, `format_deal()` and `format_analysis()` can also be used separately.

## Project layout

- `src/consts/` — shared enums (`Suit`, `Strain`, `Seat`, `Vulnerability`) and constants, numbered as DDS expects.
- `src/models/sampler/` — Pydantic models: `Card`, `Hand`, `Deal`, `Deck` (`cards.py`) and `DealAnalysis` (`analysis.py`).
- `src/models/bidding/` — Pydantic models: `Call`, `BiddingHistory`, `Contract`.
- `src/sampler/` — `DealSampler`: dealing, DDS analysis and report formatting.
- `tests/` — pytest suite (`test_smoke.py` checks the DDS wheel, `test_sampler.py` covers the sampler, `test_bidding.py` covers the bidding models).
- `Makefile` — builds the DDS wheel and wraps common commands (`make help` lists targets).

## Building DDS

Bridge analysis relies on the [DDS](https://github.com/dds-bridge/dds) double-dummy solver, which is built from source via Bazel and vendored as a local wheel. Prerequisites: `make`, [`bazelisk`](https://github.com/bazelbuild/bazelisk) (the recommended Bazel launcher — install it as `bazel` on your `PATH`), a C++ compiler (clang 15+ / GCC 11+), Python 3.14+, and `uv`.

DDS ships no `.bazelversion`, so the `build-dds` target writes one into the clone to pin the Bazel version bazelisk uses (default `7.4.1`, per DDS's recommended Bazel 7.x). Override with `make build-dds BAZEL_VERSION=7.x.y` if needed. DDS downloads its own LLVM/clang toolchain through Bazel, so no separate LLVM install is required.

To bootstrap the project end-to-end:

```bash
make install
```

This clones the DDS repo (pinned to `DDS_REF`, default `v3.0.0`) into `.dds-src/`, builds the `dds3` wheel via `bazel build -c opt //python:dds3_wheel_dist`, copies it into `vendor/`, and then runs `uv sync` so the wheel is installed into the project's virtual environment. The pinned DDS revision is configurable on the command line, e.g. `make build-dds DDS_REF=main`. Both `.dds-src/` and `vendor/` are gitignored — bumping `DDS_REF` and re-running `make install` is enough to refresh.

Other targets: `make sync` (re-run `uv sync` only), `make test` (run pytest), `make sample` (print a random analyzed deal), `make verify-dds` (run DDS's upstream tests), `make clean-dds` (drop DDS source + vendor wheel), `make clean` (also drops `.venv/` and `uv.lock`).

## Bidding models

Pure-Python building blocks for the auction (no LLM, no LangGraph yet), in `src/models/bidding/`:

- `Call` — a bid, pass, double or redouble.
- `BiddingHistory` — dealer plus ordered calls; checks legality, detects the end of the auction and derives the contract. `add()` mutates it in place.
- `Contract` — level, strain, declarer and doubling of the finished auction.

Next: a LangGraph bidding graph with a deterministic supervisor and four LLM players.
