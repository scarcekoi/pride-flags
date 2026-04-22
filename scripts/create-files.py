#!/usr/bin/env python3

import os
import subprocess
import sys
import yaml

from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from shutil import which
from tqdm import tqdm

flags_file = Path("./resources/flags.yml")
themes_dir = Path("./themes")

with flags_file.open("r") as f:
    flags_data = yaml.safe_load(f)

if len(sys.argv) != 2:
    print("Usage: ./scripts/create-files.py <flag_name|all>")
    sys.exit(1)

target = sys.argv[1].lower()


def get_flag_parent(p_flag_config):
    """Extract parent directory from flag config, or use flag name as default."""
    if isinstance(p_flag_config, dict):
        return p_flag_config.get("parent")
    return None


if target == "all":
    flags_to_process = [
        (key, get_flag_parent(config) or key)
        for key, config in flags_data.get("flags", {}).items()
    ]
else:
    if target not in flags_data.get("flags", {}):
        print(f"Flag '{target}' not found in flags.yml")
        sys.exit(1)
    flag_config = flags_data.get("flags", {})[target]
    parent = get_flag_parent(flag_config) or target
    flags_to_process = [(target, parent)]

formats = ["ase", "aseprite", "bmp", "flc", "jpeg", "jpg", "pcx", "pcc", "qoi",
           "tga", "webp"]

# Format routing: which tool handles each format best
ASEPRITE_FORMATS = {"ase", "aseprite", "bmp", "flc", "pcx", "pcc", "tga"}
IMAGEMAGICK_FORMATS = {"jpg", "jpeg", "webp", "qoi"}

# Tool detection
CONVERT = which("convert") or ""
ASEPRITE = which("aseprite") or which("libresprite") or ""

if not CONVERT:
    raise RuntimeError("ImageMagick (convert) not found on system!")
if not ASEPRITE:
    raise RuntimeError("Neither aseprite nor libresprite found on system!")


def export_svg_to_png(svg_path: Path) -> Path:
    """Convert SVG to PNG using cairosvg."""
    png_path = svg_path.with_suffix(".png")

    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=96)
        return png_path
    except ImportError:
        print("ERROR: cairosvg not installed. Run: pip install cairosvg",
              file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"cairosvg failed for {svg_path}: {e}", file=sys.stderr)
        return None


def convert_png_to_format(png_path: Path, fmt: str) -> bool:
    """Convert PNG to target format using the best tool for that format."""
    output_path = png_path.with_stem(
        png_path.stem.replace(".png", "")).with_suffix(f".{fmt}")

    # Route to the best tool
    if fmt in ASEPRITE_FORMATS:
        cmd = [ASEPRITE, "-b", str(png_path), "--save-as", str(output_path)]
    elif fmt == "webp":
        cmd = [CONVERT, str(png_path), "-define", "webp:lossless=true",
               str(output_path)]
    else:
        cmd = [CONVERT, str(png_path), str(output_path)]

    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.run(cmd, check=True, stdout=devnull, stderr=devnull,
                           timeout=10)
        return True
    except Exception as e:
        print(f"Failed {fmt} for {png_path}: {e}", file=sys.stderr)
        return False


def convert_png_to_all_formats(png_path: Path) -> int:
    """Parallel format conversion for a single PNG."""
    success_count = 0

    with ProcessPoolExecutor(max_workers=4) as fmt_executor:
        fmt_futures = {
            fmt_executor.submit(convert_png_to_format, png_path, fmt): fmt
            for fmt in formats
        }

        for future in as_completed(fmt_futures):
            if future.result():
                success_count += 1

    return success_count


def batch_export_svgs(svg_paths: list[Path]) -> dict[Path, Path]:
    """Parallel SVG→PNG export for a batch of SVGs."""
    results = {}

    with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
        futures = {
            executor.submit(export_svg_to_png, svg): svg
            for svg in svg_paths
        }

        for future in as_completed(futures):
            svg = futures[future]
            png = future.result()
            if png:
                results[svg] = png

    return results


def process_flag_theme(flag_key: str, parent_dir: str, theme_dir: Path) -> \
    tuple[str, str, int]:
    """Process a single flag/theme combo: SVG → PNG → all formats."""
    svg_path = theme_dir / parent_dir / f"{flag_key}.svg"
    if not svg_path.exists():
        return flag_key, theme_dir.name, 0

    png_path = export_svg_to_png(svg_path)
    if not png_path:
        return flag_key, theme_dir.name, 0

    # Parallel format conversion
    success_count = convert_png_to_all_formats(png_path)

    return flag_key, theme_dir.name, success_count


def main() -> None:
    theme_dirs = [d for d in themes_dir.iterdir() if d.is_dir()]
    work_queue = [
        (flag_key, parent_dir, theme_dir)
        for flag_key, parent_dir in flags_to_process
        for theme_dir in theme_dirs
    ]

    if not work_queue:
        print("No work to do!", file=sys.stderr)
        return

    # Cap workers to avoid resource thrashing
    max_workers = min(cpu_count() - 1, len(work_queue), 8)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_flag_theme, flag_key, parent_dir,
                            theme_dir): (flag_key, theme_dir.name)
            for flag_key, parent_dir, theme_dir in work_queue
        }

        with tqdm(total=len(futures), desc="Processing",
                  unit="flag/theme") as pbar:
            for future in as_completed(futures):
                flag_key, theme_name, success_count = future.result()
                status = ":3" if success_count == len(
                    formats) else "⚠" if success_count > 0 else "3:"
                pbar.update(1)
                pbar.write(
                    f"{status} {flag_key}/{theme_name}: {success_count}/{len(formats)}")

    print(f"\n:3 All files exported via cairosvg + aseprite/imagemagick.")


if __name__ == "__main__":
    main()
