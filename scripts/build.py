#!/usr/bin/env python3
"""
Asset pipeline: templates → exports → composites → optimisation.
Subcommands: templates, export, composite, optimise, all.
"""

import os
import re
import subprocess
import sys
import yaml

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from multiprocessing import cpu_count
from pathlib import Path
from shutil import which
from tqdm import tqdm

# --- Constants ---
FLAVOURS = ["latte", "frappe", "macchiato", "mocha"]
DIST_DIR = Path("dist/release")
FLAGS_DIR = DIST_DIR / "flags"
FLAVOURS_DIR = DIST_DIR / "flavours"
FLAGS_FILE = Path("resources/flags.yml")
CATEGORIES_FILE = Path("resources/categories.yml")
README_FILE = Path("README.md")
THEMES_DIR = Path("themes")

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


def m_ensure_dirs() -> None:
    """Create output directories."""
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    FLAVOURS_DIR.mkdir(parents=True, exist_ok=True)


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


# --- Stage 2: SVG → PNG → Formats ---
def m_export_svg_to_png(p_svg_path: Path) -> Path | None:
    """Convert SVG to PNG. Returns path or None on fail."""
    try:
        import cairosvg
    except ImportError:
        print("✗ cairosvg not installed. run: pip install cairosvg",
              file=sys.stderr)
        sys.exit(1)

    l_png_path = p_svg_path.with_suffix(".png")
    try:
        cairosvg.svg2png(url=str(p_svg_path), write_to=str(l_png_path), dpi=96)
        return l_png_path
    except Exception as p_e:
        print(f"svg render failed: {p_svg_path.name} ({p_e})", file=sys.stderr)
        return None


def m_convert_png_to_format(p_png: Path, p_fmt: str, p_aseprite: str,
                            p_convert: str) -> bool:
    """Convert PNG to a specific format."""
    l_output = p_png.with_suffix(f".{p_fmt}")

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
    except subprocess.CalledProcessError:
        return False


def m_export_flag(p_flag: str, p_parent: str, p_theme: Path, p_aseprite: str,
                  p_convert: str) -> tuple[str, str, int]:
    """Export single flag: SVG → PNG → all formats."""
    l_svg = p_theme / p_parent / f"{p_flag}.svg"

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

        with tqdm(total=len(l_futures), unit="combo",
                  desc="exporting") as l_pbar:
            for l_future in as_completed(l_futures):
                l_flag, l_theme, l_count = l_future.result()
                l_ok = l_count == len(EXPORT_FORMATS)
                l_sym = "✓" if l_ok else ("⚠" if l_count > 0 else "✗")
                l_pbar.update(1)
                l_pbar.write(
                    f"{l_sym} {l_flag}/{l_theme}: {l_count}/{len(EXPORT_FORMATS)}")

                if not l_ok:
                    l_failed.append((l_flag, l_theme))

    if l_failed:
        print(f"\n✗ {len(l_failed)} exports incomplete", file=sys.stderr)
        return False

    print(f":3 exported {len(l_work)} flag/theme combos")
    return True


# --- Stage 3: Composite Assembly ---
def m_run_catwalk(p_flag: str, p_parent: str, p_layout: str,
                  p_flavours: list[str]) -> tuple[str, bool, str]:
    """Execute catwalk for flag+layout."""
    l_inputs = [f"themes/{l_f}/{p_parent}/{p_flag}.webp" for l_f in p_flavours]
    l_output = f"assets/{p_layout}/{p_flag}.webp"

    l_cmd = ["catwalk", *l_inputs, "-o", l_output, "-l", p_layout, "-r", "0"]

    l_result = subprocess.run(l_cmd, capture_output=True, text=True, timeout=15)
    return f"{p_flag}:{p_layout}", l_result.returncode == 0, l_result.stderr


def m_stage_composite(p_flags: dict[str, str]) -> bool:
    """Generate composite assets via catwalk."""
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
            l_executor.submit(m_run_catwalk, l_f, l_p, l_l, FLAVOURS): (l_f,
                                                                        l_l)
            for l_f, l_p, l_l in l_work
        }

        with tqdm(total=len(l_futures), unit="composite",
                  desc="compositing") as l_pbar:
            for l_future in as_completed(l_futures):
                l_status, l_ok, l_err = l_future.result()
                l_sym = "✓" if l_ok else "✗"
                l_pbar.update(1)
                l_pbar.write(f"{l_sym} {l_status}" + (
                    f" ({l_err[:40]})" if not l_ok else ""))

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

        with tqdm(total=len(l_futures), unit="file",
                  desc="optimizing") as l_pbar:
            for l_future in as_completed(l_futures):
                l_path, l_ok, l_err = l_future.result()
                l_sym = "✓" if l_ok else "✗"
                l_pbar.update(1)
                l_pbar.write(f"{l_sym} {l_path.name}" + (
                    f" ({l_err[:35]})" if not l_ok else ""))
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


# --- Stage 5: Packaging ---
def m_create_theme_archives() -> bool:
    """Create tar.xz for each theme."""
    print(f"packaging {len(FLAVOURS)} themes...")
    l_failed = []

    for l_theme in tqdm(FLAVOURS, desc="themes", unit="theme"):
        l_src = THEMES_DIR / l_theme
        l_dest = FLAVOURS_DIR / f"{l_theme}.tar.xz"

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
            tqdm.write(f"  ✗ {l_theme}")
        else:
            tqdm.write(f"  ✓ {l_theme}")

    return _flag_check(l_failed, len(FLAVOURS))


def m_create_flag_archives(p_flags: dict[str, str]) -> bool:
    """Create tar.xz for each flag (combining all themes)."""
    print(f"packaging {len(p_flags)} flags...")
    l_failed = []

    for l_flag, l_parent in tqdm(p_flags.items(), desc="flags", unit="flag"):
        l_dest = FLAGS_DIR / f"{l_flag}.tar.xz"
        l_dest.unlink(missing_ok=True)

        l_tar_paths = []
        for l_theme in FLAVOURS:
            l_flag_dir = THEMES_DIR / l_theme / l_parent
            if l_flag_dir.exists():
                # Glob all files in the directory
                l_files = list(l_flag_dir.glob("*"))
                for l_file in l_files:
                    # Store as theme/filename
                    l_rel = l_file.relative_to(THEMES_DIR)
                    l_tar_paths.append(str(l_rel))

        if not l_tar_paths:
            tqdm.write(f"  ⚠ {l_flag} has no assets")
            continue

        l_result = subprocess.run(
            ["tar", "-I", "xz -T0 -c -z --best", "-cf", str(l_dest),
             "-C", str(THEMES_DIR), "--exclude", ".*", *l_tar_paths],
            capture_output=True,
            text=True,
            timeout=30
        )

        if l_result.returncode != 0:
            l_failed.append((l_flag, l_result.stderr))
            tqdm.write(f"  ✗ {l_flag}")
        else:
            tqdm.write(f"  ✓ {l_flag}")

    return _flag_check(l_failed, len(p_flags))


def m_stage_package_archives(p_flags: dict[str, str]) -> bool:
    """Create tar.xz archives for themes and flags."""
    m_ensure_dirs()
    l_ok = m_create_theme_archives() and m_create_flag_archives(p_flags)

    if l_ok:
        print(f"✓ packaged to {DIST_DIR}")
    return l_ok


# --- CLI Dispatcher ---
def m_main() -> int:
    """Run pipeline stages."""
    if len(sys.argv) < 2:
        print("usage: ./scripts/build.py <command>")
        print("commands: templates, export, composite, optimize, all")
        return 1

    l_command = sys.argv[1].lower()
    l_flags = m_load_flags()

    l_stages = {
        "templates": m_process_templates,
        "export": lambda: m_stage_export(l_flags),
        "composite": lambda: m_stage_composite(l_flags),
        "optimize": m_stage_optimize,
        "readme": lambda: m_stage_update_readme(),
        "package": lambda: m_stage_package_archives(l_flags),
    }

    if l_command == "all":
        l_stages_to_run = [
            ("templates", m_process_templates),
            ("export", lambda: m_stage_export(l_flags)),
            ("composite", lambda: m_stage_composite(l_flags)),
            ("optimize", m_stage_optimize),
            ("readme", lambda: m_stage_update_readme()),
            ("package", lambda: m_stage_package_archives(l_flags)),
        ]
    elif l_command in l_stages:
        l_stages_to_run = [(l_command, l_stages[l_command])]
    else:
        print(f"unknown command: {l_command}", file=sys.stderr)
        return 1

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
    sys.exit(m_main())
