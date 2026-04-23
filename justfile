# Simple justfile to interface with the pyproject!

# First-time setup of venv (and also updates!)
setup:
    uv sync
    uv run python -m playwright install chromium

# Run full build pipeline! :3
[default]
all: setup
    uv run python scripts/build.py all

# Generate SVGs from whiskers templates
whiskers:
    uv run python scripts/build.py whiskers

# Export SVGs to PNGs, then to all other formats we support
export:
    uv run python scripts/build.py export

# Generate catwalk
catwalk:
    uv run python scripts/build.py catwalk

# Optimize all image files
optimize:
    uv run python scripts/build.py optimize

# Generate updated flaglist for README.md
readme:
    uv run python scripts/build.py readme

# Package all files to tarballs in dist/
package:
    uv run python scripts/build.py package
