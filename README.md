# bb_agents
bridge bidding agents

Python 3.14 project (managed with `uv`) for training bridge bidding agents. It contains a **deal sampler** (random bridge deals analyzed with the DDS double-dummy solver: tricks per strain and declarer, plus par score and contract) and a **bidding table**: four LLM players bid a deal in a LangGraph graph.

## Quick start

```bash
make install   # build DDS wheel + uv sync (see "Building DDS" below)
make test      # run the pytest suite
make sample    # print a random deal with its double-dummy analysis
make sample SEED=42   # same, but reproducible
make bid       # play one auction with LLM players (needs an API key)
make bid ARGS="--seed 42 --config config/bidding.toml"
```

## Using the sampler

```python
from consts import Vulnerability
from sampler import DealSampler

sampler = DealSampler(seed=42)  # seed is optional
deal, analysis = sampler.sample_and_analyze(Vulnerability.NONE)
print(DealSampler.format_report(deal, analysis))
```

The report contains the PBN string, the hands per seat, a strain-by-seat table of double-dummy tricks, and the par score and contract. `sample_deal()` and `analyze()` can also be used separately, and the models render themselves: `Deal.format()`, `Deal.to_dict()`, `Hand.to_str()`, `DealAnalysis.format()`.

Hands and deals can also be parsed back:

```python
from models.cards import Deal, Hand

hand = Hand.from_str("♠ AKQ  ♥ T98  ♦ J2  ♣ 5432")   # readable form
hand = Hand.from_str("AKQ.T98.J2.5432")              # PBN form
deal = Deal.from_dict({"N": "...", "E": "...", "S": "...", "W": "..."})
```

`Deal.from_dict` is the inverse of `Deal.to_dict`. `DealAnalysis.from_dds(table, par)` builds an analysis from raw `dds3.calc_dd_table` / `dds3.par` output. Parsing raises `ValueError` for malformed text, a hand without 13 distinct cards, a missing seat, or a card held by two seats.

## Bidding

`make bid` samples a deal, plays the auction and streams each step: the player's proposed call with its reasoning, then whether the call was accepted or rejected, and finally the auction table.

**How a turn works.** The graph (`create_supervisor()` in `src/agents/supervisor.py`) has two nodes:

- `player_bid` — asks the player on turn for a call. The player sees the dealer, the vulnerability, its own hand, the auction as a list (`NORTH: P`, `EAST: 1S`, ...) and only its own earlier reasoning. The system prompt names its seat, partner, opponents and convention.
- `route_bid_turn` — validates the proposed call against the auction. A legal call is added to the history. An illegal one is sent back with the rejected call and its reasoning, up to `max_try_nb` times (4 by default); after that the player is forced to pass.

After `route_bid_turn` the graph ends once the auction is over, otherwise the next player bids. Deal sampling is not part of the graph: the deal is given in the initial state as a `Deal`, and the seat on turn is always `history.next_seat`.

**Players.** Each seat is a chat model with structured output (`PlayerReply`: `reasoning` and `call`), built by `create_player()` in `src/agents/player.py` with LangChain's `init_chat_model`. Players are passed to the graph through the runtime context.

**Configuration** lives in `config/bidding.toml`, one table per seat:

```toml
[players.NORTH]
model = "google_genai:gemini-3.1-flash-lite"  # "<provider>:<model name>"
convention = "SAYC"                           # or "2/1 Force Game"
timeout = 60        # optional: seconds to wait for a reply
max_retries = 1     # optional: retries after a failed request
```

To play a seat with Claude Code instead of an API model, use the `claude_code:` prefix with a model alias, e.g. `model = "claude_code:sonnet"` (or `opus`, `haiku`). The seat then runs `claude -p` from `src/agents/player_claude_code.py`: it needs the `claude` CLI on `PATH`, counts against your Claude subscription, takes several seconds per bid, runs with tools disabled and with the player prompt in place of the default Claude Code one, and starts in an empty temp directory so no `CLAUDE.md` is loaded. `timeout` and `max_retries` apply to the `claude` call. API and Claude Code seats can be mixed.

All four seats are required, and partners (NORTH/SOUTH, EAST/WEST) must play the same convention. API keys are read from the environment as the provider expects (e.g. `GOOGLE_API_KEY`).

**From code**, `src/agents/run_bidding.py` has `run_bidding(deal, config)` (takes a `Deal`, returns the final `BiddingState`) and `stream_bidding()` (yields LangGraph `(mode, chunk)` pairs, `updates` and `values`). `scripts/play_bidding.py` is a thin wrapper around them.

## Project layout

```text
bb_agents/
├── config/
│   └── bidding.toml          # model and convention per seat
├── scripts/
│   └── play_bidding.py       # command behind `make bid`
├── src/
│   ├── agents/
│   │   ├── player.py         # prompts, create_player
│   │   ├── player_claude_code.py  # players run through `claude -p`
│   │   ├── supervisor.py     # graph nodes, create_supervisor
│   │   └── run_bidding.py    # run_bidding, stream_bidding
│   ├── consts/               # enums and constants, numbered as DDS expects
│   ├── models/
│   │   ├── bidding/          # auction rules (Call, BiddingHistory,
│   │   │                     # Contract), graph state, config
│   │   ├── cards/            # Card, Hand, Deal, Deck (shared by
│   │   │                     # the sampler and the bidding)
│   │   └── sampler/          # DealAnalysis
│   └── sampler/              # DealSampler: dealing, DDS analysis, reports
├── tests/
│   ├── test_agents.py        # graph, prompts, config; no LLM calls
│   ├── test_bidding.py       # Call, BiddingHistory
│   ├── test_player_claude_code.py  # Claude Code player, CLI mocked
│   ├── test_cards.py         # Card, Hand, Deal, Deck; parsing
│   ├── test_sampler.py       # sampling, DDS analysis, reports
│   └── test_smoke.py         # checks the DDS wheel
├── Makefile                  # `make help` lists targets
└── pyproject.toml
```

`.dds-src/` and `vendor/` are created by `make install` and are gitignored.

## Building DDS

Bridge analysis relies on the [DDS](https://github.com/dds-bridge/dds) double-dummy solver, which is built from source via Bazel and vendored as a local wheel. Prerequisites: `make`, [`bazelisk`](https://github.com/bazelbuild/bazelisk) (the recommended Bazel launcher — install it as `bazel` on your `PATH`), a C++ compiler (clang 15+ / GCC 11+), Python 3.14+, and `uv`.

DDS ships no `.bazelversion`, so the `build-dds` target writes one into the clone to pin the Bazel version bazelisk uses (default `7.4.1`, per DDS's recommended Bazel 7.x). Override with `make build-dds BAZEL_VERSION=7.x.y` if needed. DDS downloads its own LLVM/clang toolchain through Bazel, so no separate LLVM install is required.

To bootstrap the project end-to-end:

```bash
make install
```

This clones the DDS repo (pinned to `DDS_REF`, default `v3.0.0`) into `.dds-src/`, builds the `dds3` wheel via `bazel build -c opt //python:dds3_wheel_dist`, copies it into `vendor/`, and then runs `uv sync` so the wheel is installed into the project's virtual environment. The pinned DDS revision is configurable on the command line, e.g. `make build-dds DDS_REF=main`. Both `.dds-src/` and `vendor/` are gitignored — bumping `DDS_REF` and re-running `make install` is enough to refresh.

Other targets: `make sync` (re-run `uv sync` only), `make test` (run pytest), `make sample` (print a random analyzed deal), `make verify-dds` (run DDS's upstream tests), `make clean-dds` (drop DDS source + vendor wheel), `make clean` (also drops `.venv/` and `uv.lock`).
