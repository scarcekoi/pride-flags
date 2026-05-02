.PHONY: _setup all prepare whiskers lint fmt export catwalk optimize readme package _tools

_tools:
	@command -v optipng >/dev/null 2>&1 || (echo "[ERROR] optipng missing. Install with your package manager: optipng" && exit 1)
	@command -v svgo >/dev/null 2>&1 || (echo "[ERROR] svgo missing. Install with your package manager or with npm (npm install -g svgo)" && exit 1)
	@command -v jpegoptim >/dev/null 2>&1 || (echo "[ERROR] jpegoptim missing. Install with your package manager: jpegoptim" && exit 1)
	@echo "[OK] All external tools found"

# Setup! uv sync and playwright fetch :3
_setup: _tools
	@echo "[SETUP] Installing Python dependencies..."
	uv sync --all-extras
	@echo "[SETUP] Installing Playwright..."
	uv run python -m playwright install chromium
	@echo "[OK] Setup complete :3"

# Run full build pipeline! :3
.DEFAULT_GOAL := all
all: prepare
	@echo "[BUILD] Running full pipeline..."
	uv run python scripts/build.py all
	@echo "[OK] Build complete :3"

# Prepare! setup, lint, fmt :3
prepare: _setup lint fmt
	@echo "[OK] Preparation complete :3"

# Generate SVGs from whiskers templates
whiskers:
	@echo "[WHISKERS] Generating SVGs from templates..."
	uv run python scripts/build.py whiskers
	@echo "[OK] SVGs generated :3"

# Linter! Lint everything! (note: whiskers check is included in whiskers!)
lint:
	@echo "[LINT] Checking YAML..."
	yamllint .
	@echo "[LINT] Checking Python with ruff..."
	uv run ruff check scripts/build.py
	@echo "[LINT] Type-checking with mypy..."
	uv run mypy scripts/build.py
	@echo "[OK] Linting passed :3"

# Format all code!
fmt:
	@echo "[FMT] Formatting YAML..."
	yamlfix .
	@echo "[FMT] Formatting TOML..."
	taplo format
	@echo "[FMT] Formatting Markdown..."
	mdformat .
	@echo "[FMT] Formatting Python..."
	uv run ruff format scripts/build.py
	@echo "[OK] Formatting complete :3"

# Export SVGs to PNGs, then to all other formats we support
export:
	@echo "[EXPORT] Exporting images..."
	uv run python scripts/build.py export
	@echo "[OK] Export complete :3"

# Generate catwalk
catwalk:
	@echo "[CATWALK] Generating catwalk..."
	uv run python scripts/build.py catwalk
	@echo "[OK] Catwalk generated :3"

# Optimize all image files
optimize:
	@echo "[OPTIMIZE] Optimizing images..."
	uv run python scripts/build.py optimize
	@echo "[OK] Optimization complete :3"

# Generate updated flag-list for README.md
readme:
	@echo "[README] Updating flag list..."
	uv run python scripts/build.py readme
	@echo "[OK] README updated :3"

# Package all files to tarballs in dist/
package:
	@echo "[PACKAGE] Creating distribution tarballs..."
	uv run python scripts/build.py package
	@echo "[OK] Packaging complete :3"
