.PHONY: help install sync test sample build-dds verify-dds clean-dds clean

# DDS source configuration — override on the command line if needed, e.g.
#   make build-dds DDS_REF=main
DDS_REPO ?= https://github.com/dds-bridge/dds.git
DDS_REF  ?= v3.0.0
DDS_DIR  ?= .dds-src

# Bazel version to build DDS with. Resolved by bazelisk (the recommended
# Bazel launcher) via the .bazelversion file we drop into the clone. DDS
# ships no .bazelversion of its own, so without this bazelisk would grab
# "latest" — pin it for reproducible builds. DDS docs recommend Bazel 7.x.
BAZEL_VERSION ?= 7.4.1

VENDOR_DIR := vendor
DDS_WHEEL  := $(VENDOR_DIR)/dds3-1.0.0-py3-none-any.whl

help:
	@echo "Targets:"
	@echo "  install    - clone+build DDS wheel, then 'uv sync'"
	@echo "  build-dds  - clone DDS@$(DDS_REF) and build wheel into $(VENDOR_DIR)/"
	@echo "  sync       - run 'uv sync' (assumes vendor wheel already built)"
	@echo "  test       - run this project's pytest suite"
	@echo "  sample     - print a random deal + DD analysis (optional SEED=<int>)"
	@echo "  verify-dds - run DDS's upstream tests against the installed wheel"
	@echo "  clean-dds  - remove $(DDS_DIR) and $(VENDOR_DIR)"
	@echo "  clean      - clean-dds plus .venv and uv.lock"

install: $(DDS_WHEEL) sync

$(DDS_DIR)/.git:
	git clone $(DDS_REPO) $(DDS_DIR)
	cd $(DDS_DIR) && git checkout $(DDS_REF)

$(DDS_WHEEL): $(DDS_DIR)/.git
	echo "$(BAZEL_VERSION)" > $(DDS_DIR)/.bazelversion
	cd $(DDS_DIR) && bazel build -c opt //python:dds3_wheel_dist
	mkdir -p $(VENDOR_DIR)
	cp $(DDS_DIR)/bazel-bin/python/dist/dds3-*.whl $(VENDOR_DIR)/

build-dds: $(DDS_WHEEL)

sync:
	uv sync

# Run this project's tests.
test:
	uv run pytest -v

# Print a random deal and its double-dummy analysis. SEED is optional.
SEED ?= None
sample:
	uv run python -c "from sampler import DealSampler as D; \
	d, a = D($(SEED)).sample_and_analyze(); \
	print(D.format_report(d, a))"

# Run DDS's own upstream test suite (in $(DDS_DIR), gitignored & regenerated)
# as a build-acceptance gate. PYTHONPATH follows DDS's docs/python_interface.md:
#   python          -> dds3 source package + the test_utils helper
#   bazel-bin/python -> the built _dds3.so (dds3/__init__.py's fallback import)
# `uv run --project` forces our venv (for pytest); this validates the freshly
# built bazel artifact.
verify-dds:
	PYTHONPATH=$(CURDIR)/$(DDS_DIR)/python:$(CURDIR)/$(DDS_DIR)/bazel-bin/python \
		uv run pytest $(DDS_DIR)/python/tests/ -v

clean-dds:
	rm -rf $(DDS_DIR) $(VENDOR_DIR)

clean: clean-dds
	rm -rf .venv uv.lock
