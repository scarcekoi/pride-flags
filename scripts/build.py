"""
Asset pipeline: templates → exports → composites → optimisation.
Subcommands: templates, export, composite, optimise, all.
"""

import argparse
import json
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET
import yaml

from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from glob import glob
from io import StringIO
from multiprocessing import cpu_count
from pathlib import Path
from playwright.sync_api import sync_playwright
from shutil import which

# --- Constants ---
FLAVOURS = ["latte", "frappe", "macchiato", "mocha"]
DIST_DIR = Path("dist")
ASSETS_DIR = Path("assets")
FLAGS_DIR = DIST_DIR / "flags"
FLAVOURS_DIR = DIST_DIR / "flavours"
FLAGS_FILE = Path("resources/flags.yml")
CATEGORIES_FILE = Path("resources/categories.yml")
README_FILE = Path("README.md")
THEMES_DIR = Path("themes")
CANONICAL_HEIGHT = 1000
MAX_CONVERT_RETRIES = 10
CONVERT_RETRY_DELAY = 1

EXPORT_FORMATS = ["ase", "aseprite", "bmp", "flc", "jpeg", "jpg", "pcx", "pcc",
                  "qoi", "tga", "webp"]
ASEPRITE_FORMATS = {"ase", "aseprite", "bmp", "flc", "pcx", "pcc", "tga"}
COMPOSITE_LAYOUTS = ["composite", "grid", "row"]

# --- Globals (resolved at runtime) ---
g_convert = which("convert")
g_aseprite = which("aseprite") or which("libresprite")


# --- Utility Functions ---
def m_ensure_tool(p_name: str, p_path: str | None) -> str:
    """Verify tool exists, die gracefully if missing."""
    if not p_path:
        print(f"✗ {p_name} not found. install it & try again!", file=sys.stderr)
        sys.exit(1)
    return p_path


def m_load_flags() -> dict[str, str]:
    """Load flags → parent directory mapping from YAML."""
    with FLAGS_FILE.open() as f:
        l_data = yaml.safe_load(f)

    l_flags = {}
    for l_flag_name, l_config in l_data.get("flags", {}).items():
        l_parent = l_config.get("parent") if isinstance(l_config,
                                                        dict) else l_flag_name
        l_flags[l_flag_name] = l_parent or l_flag_name

    return l_flags


def m_get_svg_dimensions(p_svg_path: Path) -> tuple[int, int] | None:
    """Extract width and height from SVG file. Returns (width, height) or None."""
    try:
        tree = ET.parse(p_svg_path)
        root = tree.getroot()

        width = root.get('width')
        height = root.get('height')

        if width and height:
            # Strip 'px' or other units if present
            width = int(float(width.rstrip('px')))
            height = int(float(height.rstrip('px')))
            return width, height
    except Exception as p_e:
        print(f"Failed to parse SVG dimensions from {p_svg_path.name}: {p_e}",
              file=sys.stderr)

    return None


def _flag_check(l_failed, l_count) -> bool:
    """Check archive results."""
    if l_failed:
        print(f"\n✗ {len(l_failed)} archives failed:", file=sys.stderr)
        for l_name, l_err in l_failed:
            print(f"  {l_name}: {l_err.strip()[:60]}", file=sys.stderr)
        return False

    print(f":3 all {l_count} archives packaged")
    return True


def m_process_templates() -> bool:
    """Process .tera files with whiskers."""
    shutil.rmtree(THEMES_DIR, ignore_errors=True)
    THEMES_DIR.mkdir(parents=True, exist_ok=True)

    l_templates_dir = Path(__file__).resolve().parent.parent / "templates"
    l_tera_files = sorted(l_templates_dir.glob("**/*.tera"))

    if not l_tera_files:
        print(f"no .tera templates found in {l_templates_dir}")
        return True

    print(f"processing {len(l_tera_files)} templates...")
    l_failed = []

    for l_file in l_tera_files:
        l_result = subprocess.run(
            ["whiskers", str(l_file)],
            capture_output=True,
            text=True,
            timeout=5
        )

        l_relative = l_file.relative_to(l_templates_dir)
        if l_result.returncode != 0:
            print(f"  ✗ {l_relative}")
            l_failed.append((l_relative, l_result.stderr))
        else:
            print(f"  ✓ {l_relative}")

    if l_failed:
        print(f"\nuh oh—{len(l_failed)}/{len(l_tera_files)} templates borked:",
              file=sys.stderr)
        for l_path, l_err in l_failed:
            print(f"  {l_path}: {l_err.strip()[:80]}", file=sys.stderr)
        return False

    print(f":3 all {len(l_tera_files)} templates good!")
    return True


def m_scan_flag_dimensions(p_parent: str, p_flavours: list[str]) -> tuple[
    int, int]:
    """Get native dimensions from the first flavour of the parent group."""
    l_path = f"themes/{p_flavours[0]}/{p_parent}/"
    l_files = sorted(glob(f"{l_path}*.webp"))

    if not l_files:
        raise ValueError(f"No webp files in {l_path}")

    with Image.open(l_files[0]) as l_img:
        return l_img.width, l_img.height

    return None


def m_get_image_paths(p_flag: str, p_parent: str, p_flavours: list[str]) -> \
    dict[str, str]:
    """Get webp for each flavour, checking subdirectory if flag != parent."""
    l_paths = {}

    for l_f in p_flavours:
        if p_flag != p_parent:
            l_path = f"themes/{l_f}/{p_parent}/{p_flag}/{p_flag}.webp"
        else:
            l_path = f"themes/{l_f}/{p_parent}/{p_flag}.webp"

        if not Path(l_path).exists():
            raise FileNotFoundError(f"No webp file at {l_path}")

        l_paths[l_f] = l_path

    return l_paths


# --- Stage 2: SVG → PNG → Formats ---
def m_export_svg_to_png(p_svg_path: Path) -> Path | None:
    """Convert SVG to PNG using Playwright. Returns path or None on fail."""
    l_png_path = p_svg_path.with_suffix(".png")
    try:
        from playwright.sync_api import sync_playwright

        # Get SVG dimensions dynamically
        l_dims = m_get_svg_dimensions(p_svg_path)
        if not l_dims:
            print(f"Could not determine SVG dimensions: {p_svg_path.name}",
                  file=sys.stderr)
            return None

        l_width, l_height = l_dims

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": l_width, "height": l_height})
            page.goto(f"file://{p_svg_path.resolve()}")
            page.screenshot(path=str(l_png_path))
            browser.close()
        return l_png_path
    except Exception as p_e:
        print(f"svg render failed: {p_svg_path.name} ({p_e})", file=sys.stderr)
        return None


def m_convert_png_to_format(p_png: Path, p_fmt: str, p_aseprite: str,
                            p_convert: str) -> bool:
    """Convert PNG to a specific format with retry logic."""
    l_output = p_png.with_suffix(f".{p_fmt}")

    for l_attempt in range(MAX_CONVERT_RETRIES):
        if p_fmt in ASEPRITE_FORMATS:
            l_cmd = [p_aseprite, "-b", str(p_png), "--save-as", str(l_output)]
        elif p_fmt == "webp":
            l_cmd = [p_convert, str(p_png), "-define", "webp:lossless=true",
                     str(l_output)]
        else:
            l_cmd = [p_convert, str(p_png), str(l_output)]

        try:
            subprocess.run(l_cmd, capture_output=True, timeout=10, check=True)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if l_attempt < MAX_CONVERT_RETRIES - 1:
                time.sleep(
                    CONVERT_RETRY_DELAY * (2 ** l_attempt))
            else:
                print(
                    f"  ✗ {p_fmt} failed for {p_png.name} after {MAX_CONVERT_RETRIES} attempts...BWEH >.<\n{e}",
                    file=sys.stderr)
                return False

    return False


def m_export_flag(p_flag: str, p_parent: str, p_theme: Path, p_aseprite: str,
                  p_convert: str) -> tuple[str, str, int]:
    """Export single flag: SVG → PNG → all formats."""
    if p_flag != p_parent:
        l_flag_dir = p_theme / p_parent / p_flag
    else:
        l_flag_dir = p_theme / p_parent

    l_svg = l_flag_dir / f"{p_flag}.svg"

    if not l_svg.exists():
        return p_flag, p_theme.name, 0

    l_png = m_export_svg_to_png(l_svg)
    if not l_png:
        return p_flag, p_theme.name, 0

    l_success = 0
    for l_fmt in EXPORT_FORMATS:
        if m_convert_png_to_format(l_png, l_fmt, p_aseprite, p_convert):
            l_success += 1

    return p_flag, p_theme.name, l_success


def m_stage_export(p_flags: dict[str, str]) -> bool:
    """Export all flags across all themes."""
    m_ensure_tool("ImageMagick (convert)", g_convert)
    m_ensure_tool("Aseprite/LibreSprite", g_aseprite)

    l_themes = sorted([d for d in THEMES_DIR.iterdir() if d.is_dir()])
    l_work = [
        (l_flag, l_parent, l_theme)
        for l_flag, l_parent in p_flags.items()
        for l_theme in l_themes
    ]

    if not l_work:
        print("nothing to export", file=sys.stderr)
        return True

    print(
        f"exporting {len(p_flags)} flags × {len(l_themes)} themes → {len(EXPORT_FORMATS)} formats...")

    l_max_workers = min(cpu_count() - 1, 8)
    l_failed = []

    with ThreadPoolExecutor(max_workers=l_max_workers) as l_executor:
        l_futures = {
            l_executor.submit(m_export_flag, l_f, l_p, l_t, g_aseprite,
                              g_convert): (l_f, l_t.name)
            for l_f, l_p, l_t in l_work
        }

        for l_future in as_completed(l_futures):
            l_flag, l_theme, l_count = l_future.result()
            l_ok = l_count == len(EXPORT_FORMATS)

            if not l_ok:
                l_sym = "⚠" if l_count > 0 else "✗"
                print(
                    f"{l_sym} {l_flag}/{l_theme}: {l_count}/{len(EXPORT_FORMATS)}")
                l_failed.append((l_flag, l_theme))

    if l_failed:
        print(f"\n✗ {len(l_failed)} exports incomplete", file=sys.stderr)
        return False

    print(f":3 exported {len(l_work)} flag/theme combos")
    return True


# --- Stage 3: Composite Assembly ---
def m_run_catwalk(
    p_flag: str,
    p_parent: str,
    p_layout: str,
    p_flavours: list[str]
) -> tuple[str, bool, str]:
    """Execute catwalk and normalize output."""
    try:
        l_paths = m_get_image_paths(p_flag, p_parent, p_flavours)
        l_output = f"assets/{p_layout}/{p_flag}.webp"

        l_cmd = [
            "catwalk",
            *[l_paths[l_f] for l_f in p_flavours],
            "-o", l_output,
            "-l", p_layout,
            "-r", "0"
        ]

        l_result = subprocess.run(l_cmd, capture_output=True, text=True,
                                  timeout=15)

        if l_result.returncode == 0:
            with Image.open(l_output) as l_img:
                if l_img.mode != 'RGBA':
                    l_img = l_img.convert('RGBA')

                l_alpha = l_img.split()[-1]
                l_bbox = l_alpha.getbbox()

                if l_bbox:
                    l_final = l_img.crop(l_bbox)
                    l_final.save(l_output, "WEBP")
                else:
                    l_img.save(l_output, "WEBP")

        return f"{p_flag}:{p_layout}", l_result.returncode == 0, l_result.stderr

    except FileNotFoundError as e:
        return f"{p_flag}:{p_layout}", False, str(e)
    except RuntimeError as e:
        return f"{p_flag}:{p_layout}", False, str(e)
    except (IOError, OSError) as e:
        return f"{p_flag}:{p_layout}", False, f"Image processing failed: {e}"


def m_stage_composite(p_flags: dict[str, str]) -> bool:
    """Generate composite assets via catwalk."""
    shutil.rmtree(ASSETS_DIR, ignore_errors=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Create layout subdirectories
    for layout in COMPOSITE_LAYOUTS:
        (ASSETS_DIR / layout).mkdir(parents=True, exist_ok=True)

    l_work = [
        (l_flag, l_parent, l_layout)
        for l_flag, l_parent in p_flags.items()
        for l_layout in COMPOSITE_LAYOUTS
    ]

    print(
        f"compositing {len(p_flags)} flags × {len(COMPOSITE_LAYOUTS)} layouts...")

    l_max_workers = min(cpu_count() - 1, 8)
    l_failed = []

    with ThreadPoolExecutor(max_workers=l_max_workers) as l_executor:
        l_futures = {
            l_executor.submit(m_run_catwalk, l_f, l_p, l_l, FLAVOURS): (
                l_f, l_l)
            for l_f, l_p, l_l in l_work
        }

        for l_future in as_completed(l_futures):
            l_status, l_ok, l_err = l_future.result()

            if not l_ok:
                l_flag, l_layout = l_futures[l_future]
                l_failed.append((l_flag, l_layout, l_err))

    if l_failed:
        print(f"\n✗ {len(l_failed)}/{len(l_work)} composites didn't work out",
              file=sys.stderr)
        return False

    print(f":3 all {len(l_work)} composites done")
    return True


# --- Stage 4: Optimization ---
def m_optimize_file(p_path: Path) -> tuple[Path, bool, str]:
    """Optimize image; tool chosen by extension."""
    l_suffix = p_path.suffix.lower()

    if l_suffix == ".png":
        l_cmd = ["optipng", "-o7", "-zm1-9", "-strip", "all", "-fix",
                 "-preserve", "-clobber", "-quiet", str(p_path)]
    elif l_suffix == ".svg":
        l_cmd = ["svgo", "--quiet", "--multipass", str(p_path)]
    elif l_suffix in (".jpg", ".jpeg"):
        l_cmd = ["jpegoptim", "--quiet", "-s", "--", str(p_path)]
    else:
        return p_path, False, "unknown file type"

    l_result = subprocess.run(l_cmd, capture_output=True, text=True, timeout=10)
    return p_path, l_result.returncode == 0, l_result.stderr


def m_stage_optimize() -> bool:
    """Optimize all images in place."""
    l_files = (
        list(Path(".").rglob("*.png")) +
        list(Path(".").rglob("*.svg")) +
        list(Path(".").rglob("*.jpg")) +
        list(Path(".").rglob("*.jpeg"))
    )

    if not l_files:
        print("no images to optimize")
        return True

    l_jobs = max(1, (os.cpu_count() or 1) - 2)
    print(f"optimizing {len(l_files)} images ({l_jobs} workers)...")

    l_failed = []
    with ThreadPoolExecutor(max_workers=l_jobs) as l_executor:
        l_futures = {l_executor.submit(m_optimize_file, l_f): l_f for l_f in
                     l_files}

        for l_future in as_completed(l_futures):
            l_path, l_ok, l_err = l_future.result()

            if not l_ok:
                l_failed.append((l_path, l_err))

    if l_failed:
        print(f"\n✗ {len(l_failed)}/{len(l_files)} optimizations hit a snag",
              file=sys.stderr)
        return False

    print(f":3 optimized {len(l_files)} images")
    return True


# --- Stage 5: README Generation ---
def m_stage_update_readme() -> bool:
    """Regenerate the flag list and preview sections in README."""

    with FLAGS_FILE.open() as f:
        l_flags_data = yaml.safe_load(f)
    with CATEGORIES_FILE.open() as f:
        l_cat_data = yaml.safe_load(f)

    l_cat_flags = {l_cat["key"]: [] for l_cat in l_cat_data}
    for l_flag_key, l_flag_info in l_flags_data.get("flags", {}).items():
        for l_cat_key in l_flag_info.get("categories", []):
            if l_cat_key in l_cat_flags:
                l_cat_flags[l_cat_key].append((l_flag_key, l_flag_info["name"]))

    for l_cat in l_cat_flags:
        l_cat_flags[l_cat].sort(key=lambda x: x[1])

    l_lines = [
        "<!-- AUTOGEN:FLAGLIST START -->",
        "<!-- the following section is auto-generated, do not edit -->\n",
    ]

    for l_category in l_cat_data:
        l_key = l_category["key"]
        l_name = l_category["name"]

        if not l_cat_flags[l_key]:
            continue

        l_lines.append("<details closed>")
        l_lines.append(f"<summary>{l_name}</summary>\n")

        for l_flag_key, l_flag_name in l_cat_flags[l_key]:
            l_themes = ", ".join(
                f"[{l_t.title()}](themes/{l_t}/{l_flag_key}/)"
                for l_t in ("mocha", "macchiato", "frappé", "latte")
            )
            l_lines.append(f"- {l_flag_name} ({l_themes})")

        l_lines.append("\n</details>\n")

    l_lines.append("<!-- AUTOGEN:FLAGLIST END -->")

    l_readme_text = README_FILE.read_text()
    l_updated = re.sub(
        r"<!-- AUTOGEN:FLAGLIST START -->.*?<!-- AUTOGEN:FLAGLIST END -->",
        "\n".join(l_lines),
        l_readme_text,
        flags=re.DOTALL,
    )
    README_FILE.write_text(l_updated)
    print("updated flag list")

    l_sorted_flags = sorted(
        l_flags_data.get("flags", {}).items(),
        key=lambda x: x[1]["name"].lower()
    )

    l_buf = StringIO()
    l_buf.write("<!-- AUTOGEN:PREVIEWS START -->\n")
    l_buf.write(
        "<!-- the following section is auto-generated, do not edit -->\n\n")

    for l_flag_key, l_flag_info in l_sorted_flags:
        l_flag_name = l_flag_info["name"]
        l_buf.write(
            f"<details closed>\n"
            f"<summary>{l_flag_name}</summary>\n"
            f'<img src="assets/composite/{l_flag_key}.webp" alt="{l_flag_name} composite" style="width:50%;"/>\n'
            f'<img src="assets/grid/{l_flag_key}.webp" alt="{l_flag_name} grid" style="width:50%;"/>\n'
            f'<img src="assets/row/{l_flag_key}.webp" alt="{l_flag_name} row" style="width:50%;"/>\n'
            f"</details>\n\n"
        )

    l_buf.write("<!-- AUTOGEN:PREVIEWS END -->")
    l_preview_section = l_buf.getvalue()

    l_readme_text = README_FILE.read_text()
    l_updated = re.sub(
        r"<!-- AUTOGEN:PREVIEWS START -->.*?<!-- AUTOGEN:PREVIEWS END -->",
        l_preview_section,
        l_readme_text,
        flags=re.DOTALL,
    )
    README_FILE.write_text(l_updated)
    print(f"updated previews for {len(l_sorted_flags)} flags")

    return True


# --- Stage 6: Packaging ---
def m_create_theme_archives() -> bool:
    """Create tar.xz for each theme."""

    print(f"packaging {len(FLAVOURS)} themes...")
    l_failed = []
    for l_theme in FLAVOURS:
        l_src = THEMES_DIR / l_theme
        l_dest = FLAVOURS_DIR / f"flavours_{l_theme}.tar.xz"

        if not l_src.exists():
            print(f"  ⚠ {l_theme} not found", file=sys.stderr)
            continue

        l_result = subprocess.run(
            ["tar", "-I", "xz -T0 -c -z --best", "-cf", str(l_dest), "-C",
             str(l_src.parent), l_theme],
            capture_output=True,
            text=True,
            timeout=60
        )

        if l_result.returncode != 0:
            l_failed.append((l_theme, l_result.stderr))
            print(f"  ✗ {l_theme}")
        else:
            print(f"  ✓ {l_theme}")

    return _flag_check(l_failed, len(FLAVOURS))


def m_create_flag_archives(p_flags: dict[str, str]) -> bool:
    """Create tar.xz for each parent (combining all variants and themes)."""

    # Group flags by parent
    l_by_parent = {}
    for l_flag, l_parent in p_flags.items():
        if l_parent not in l_by_parent:
            l_by_parent[l_parent] = []
        l_by_parent[l_parent].append(l_flag)

    print(f"packaging {len(l_by_parent)} parents...")
    l_failed = []
    for l_parent, l_flags in l_by_parent.items():
        l_dest = FLAGS_DIR / f"flags_{l_parent}.tar.xz"
        l_dest.unlink(missing_ok=True)

        l_tar_paths = []
        for l_theme in FLAVOURS:
            l_parent_dir = THEMES_DIR / l_theme / l_parent
            if l_parent_dir.exists():
                # Glob all files in the directory
                l_files = list(l_parent_dir.glob("*"))
                for l_file in l_files:
                    # Store as theme/filename
                    l_rel = l_file.relative_to(THEMES_DIR)
                    l_tar_paths.append(str(l_rel))

        if not l_tar_paths:
            print(f"  ⚠ {l_parent} has no assets")
            continue

        l_result = subprocess.run(
            ["tar", "-I", "xz -T0 -c -z --best", "-cf", str(l_dest),
             "-C", str(THEMES_DIR), "--exclude", ".*", *l_tar_paths],
            capture_output=True,
            text=True,
            timeout=30
        )

        if l_result.returncode != 0:
            l_failed.append((l_parent, l_result.stderr))
            print(f"  ✗ {l_parent}")
        else:
            print(f"  ✓ {l_parent}")

    return _flag_check(l_failed, len(l_by_parent))


def m_stage_package_archives(p_flags: dict[str, str]) -> bool:
    """Create tar.xz archives for themes and flags."""

    shutil.rmtree(DIST_DIR, ignore_errors=True)
    (DIST_DIR / "flavours").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "flags").mkdir(parents=True, exist_ok=True)

    l_ok = m_create_theme_archives() and m_create_flag_archives(p_flags)

    if l_ok:
        print(f"✓ packaged to {DIST_DIR}")
    return l_ok


def main() -> int:
    """Run pipeline stages."""
    parser = argparse.ArgumentParser(
        prog='build.py',
        description='Flag theme asset build pipeline'
    )

    subparsers = parser.add_subparsers(dest='command',
                                       help='available commands')

    # Define subcommands
    subparsers.add_parser('templates', help='Process templates')
    subparsers.add_parser('export', help='Export flags')
    subparsers.add_parser('composite', help='Generate composite assets')
    subparsers.add_parser('optimize', help='Optimize images')
    subparsers.add_parser('readme', help='Update README')
    subparsers.add_parser('package', help='Package archives')
    subparsers.add_parser('all', help='Run all stages')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    l_flags = m_load_flags()

    # Stage definitions
    l_stages = {
        "templates": m_process_templates,
        "export": lambda: m_stage_export(l_flags),
        "composite": lambda: m_stage_composite(l_flags),
        "optimize": m_stage_optimize,
        "readme": lambda: m_stage_update_readme(),
        "package": lambda: m_stage_package_archives(l_flags),
    }

    # Determine which stages to run
    if args.command == "all":
        l_stages_to_run = list(l_stages.items())
    else:
        l_stages_to_run = [(args.command, l_stages[args.command])]

    print()
    for l_name, l_stage in l_stages_to_run:
        print(f"→ {l_name}")
        try:
            l_ok = l_stage()
            if not l_ok:
                print(f"\n✗ {l_name} failed, stopping", file=sys.stderr)
                return 1
        except Exception as l_e:
            print(f"\n✗ {l_name} crashed: {l_e}", file=sys.stderr)
            return 1
        print()

    print("✓ all done! everything looks good :3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
