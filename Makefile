.PHONY: _setup all prepare whiskers lint fmt export catwalk optimize readme package

# Setup! uv sync and playwright fetch :3
_setup:
	uv sync --all-extras
	uv run python -m playwright install chromium

# Run full build pipeline! :3
.DEFAULT_GOAL := all
all: prepare
	uv run python scripts/build.py all

# Prepare! setup, lint, fmt :3
prepare: _setup lint fmt

# Generate SVGs from whiskers templates
whiskers:
	uv run python scripts/build.py whiskers

# Linter! Lint everything! (note: whiskers check is included in whiskers!)
lint:
	yamllint .
	uv run ruff check scripts/build.py
	uv run mypy scripts/build.py

# Format all code!
fmt:
	yamlfix .
	taplo format
	mdformat .
	uv run ruff format scripts/build.py

# Export SVGs to PNGs, then to all other formats we support
export:
	uv run python scripts/build.py export

# Generate catwalk
catwalk:
	uv run python scripts/build.py catwalk

# Optimize all image files
optimize:
	uv run python scripts/build.py optimize

# Generate updated flag-list for README.md
readme:
	uv run python scripts/build.py readme

# Package all files to tarballs in dist/
package:
	uv run python scripts/build.py package
