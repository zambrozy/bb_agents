.PHONY: help install sync build-dds clean-dds clean test

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
	@echo "  test       - run pytest via uv"
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

test:
	uv run pytest

clean-dds:
	rm -rf $(DDS_DIR) $(VENDOR_DIR)

clean: clean-dds
	rm -rf .venv uv.lock
