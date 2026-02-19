#!/usr/bin/env python3

import os
import subprocess
import sys
import yaml

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
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

if target == "all":
    flags_to_process = list(flags_data.get("flags", {}).keys())
else:
    if target not in flags_data.get("flags", {}):
        print(f"Flag '{target}' not found in flags.yml")
        sys.exit(1)
    flags_to_process = [target]

formats = [
    "ase", "aseprite", "bmp", "css", "flc", "fli", "jpeg", "jpg",
    "pcx", "pcc", "png", "qoi", "tga", "webp",
]

TOOL: str = which("aseprite") or which("libresprite") or ""
if not TOOL:
    raise RuntimeError("Neither aseprite nor libresprite found on system!")


def export_svg_to_png(svg_path: Path) -> Path | None:
    """Export SVG to PNG using cairosvg (pure Python, no external tools)."""
    tmp_png = svg_path.with_suffix(".tmp.png")

    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(tmp_png), dpi=96)
        return tmp_png
    except ImportError:
        print(
            "ERROR: cairosvg not installed. Run: pip install cairosvg",
            file=sys.stderr
        )
        sys.exit(1)
    except Exception as e:
        print(f"cairosvg failed for {svg_path}: {e}", file=sys.stderr)
        return None


def convert_png_to_format(tmp_png: Path, fmt: str, max_retries: int = 2) -> bool:
    """Convert PNG to target format with retry logic."""
    output_path = tmp_png.with_suffix(f".{fmt}")
    for attempt in range(max_retries):
        try:
            with open(os.devnull, 'w') as devnull:
                subprocess.run(
                    [TOOL, "-b", str(tmp_png), "--save-as", str(output_path)],
                    check=True,
                    stdout=devnull,
                    stderr=devnull,
                    timeout=30,
                )
            return True
        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                print(f"Timeout for {fmt}, retrying...", file=sys.stderr)
        except subprocess.CalledProcessError:
            print(f"Conversion to {fmt} failed", file=sys.stderr)
            return False
    return False


def process_flag_theme(flag_key: str, theme_dir: Path) -> tuple[str, str, int]:
    """Process a single flag/theme combo."""
    svg_path = theme_dir / flag_key / f"{flag_key}.svg"

    if not svg_path.exists():
        return (flag_key, theme_dir.name, 0)

    tmp_png = export_svg_to_png(svg_path)
    if not tmp_png:
        return (flag_key, theme_dir.name, 0)

    # Parallelize format conversions
    with ThreadPoolExecutor(max_workers=4) as fmt_executor:
        futures = [
            fmt_executor.submit(convert_png_to_format, tmp_png, fmt)
            for fmt in formats
        ]
        success_count = sum(1 for f in futures if f.result())

    tmp_png.unlink()
    return (flag_key, theme_dir.name, success_count)


def main() -> None:
    theme_dirs = [d for d in themes_dir.iterdir() if d.is_dir()]
    work_queue = [
        (flag_key, theme_dir)
        for flag_key in flags_to_process
        for theme_dir in theme_dirs
    ]

    if not work_queue:
        print("No work to do!", file=sys.stderr)
        return

    max_workers = min(cpu_count(), len(work_queue))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(process_flag_theme, flag_key, theme_dir):
                (flag_key, theme_dir.name)
            for flag_key, theme_dir in work_queue
        }

        total = len(future_to_task)

        for future in tqdm(
            as_completed(future_to_task.keys()),
            total=total,
            desc="Processing"
        ):
            flag_key, theme_name, success_count = future.result()
            status = "✓" if success_count > 0 else "✗"
            tqdm.write(f"{status} {flag_key}/{theme_name}: {success_count}/{len(formats)} formats")

    print(f"\n✓ All files exported via cairosvg + {TOOL}.")


if __name__ == "__main__":
    main()
