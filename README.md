# bb_agents
bridge bidding agents

## Building DDS

Bridge analysis relies on the [DDS](https://github.com/dds-bridge/dds) double-dummy solver, which is built from source via Bazel and vendored as a local wheel. Prerequisites: `make`, [`bazelisk`](https://github.com/bazelbuild/bazelisk) (the recommended Bazel launcher — install it as `bazel` on your `PATH`), a C++ compiler (clang 15+ / GCC 11+), Python 3.14+, and `uv`.

DDS ships no `.bazelversion`, so the `build-dds` target writes one into the clone to pin the Bazel version bazelisk uses (default `7.4.1`, per DDS's recommended Bazel 7.x). Override with `make build-dds BAZEL_VERSION=7.x.y` if needed. DDS downloads its own LLVM/clang toolchain through Bazel, so no separate LLVM install is required.

To bootstrap the project end-to-end:

```bash
make install
```

This clones the DDS repo (pinned to `DDS_REF`, default `v3.0.0`) into `.dds-src/`, builds the `dds3` wheel via `bazel build -c opt //python:dds3_wheel_dist`, copies it into `vendor/`, and then runs `uv sync` so the wheel is installed into the project's virtual environment. The pinned DDS revision is configurable on the command line, e.g. `make build-dds DDS_REF=main`. Both `.dds-src/` and `vendor/` are gitignored — bumping `DDS_REF` and re-running `make install` is enough to refresh.

Other targets: `make sync` (re-run `uv sync` only), `make test` (run pytest), `make clean-dds` (drop DDS source + vendor wheel), `make clean` (also drops `.venv/` and `uv.lock`).
