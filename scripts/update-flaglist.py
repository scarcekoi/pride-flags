#!/usr/bin/env python3

import asyncio
import sys
import yaml

from pathlib import Path
from shutil import which
from multiprocessing import cpu_count
from tqdm.asyncio import tqdm

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

FAST_FORMATS = ("png", "bmp", "webp", "jpg", "jpeg")
SLOW_FORMATS = (
    "ase",
    "aseprite",
    "tga",
    "qoi",
    "flc",
    "fli",
    "pcx",
    "pcc",
    "css"
)

TOOL: str = which("aseprite") or which("libresprite") or ""
if not TOOL:
    raise RuntimeError("Neither aseprite nor libresprite found on system!")

THEME_DIRS = tuple(d for d in themes_dir.iterdir() if d.is_dir())

# Aggressive semaphores
SVG_SEMAPHORE = asyncio.Semaphore(cpu_count())
FORMAT_SEMAPHORE = asyncio.Semaphore(cpu_count() * 2)


async def export_svgs_batch(svg_paths: list[Path]) -> dict[Path, Path | None]:
    """Batch render multiple SVGs."""
    loop = asyncio.get_event_loop()

    async with SVG_SEMAPHORE:
        def _render_batch():
            import cairosvg
            results = {}
            for svg_path in svg_paths:
                tmp_png = svg_path.with_suffix(".tmp.png")
                try:
                    cairosvg.svg2png(
                        url=str(svg_path),
                        write_to=str(tmp_png),
                        dpi=72
                    )
                    results[svg_path] = tmp_png
                except Exception as e:
                    print(
                        f"cairosvg failed for {svg_path}: {e}",
                        file=sys.stderr
                    )
                    results[svg_path] = None
            return results

        return await loop.run_in_executor(None, _render_batch)


async def convert_png_to_format(tmp_png: Path, fmt: str) -> bool:
    """Convert PNG to format asynchronously."""
    output_path = tmp_png.with_suffix(f".{fmt}")

    async with FORMAT_SEMAPHORE:
        try:
            proc = await asyncio.create_subprocess_exec(
                TOOL,
                "-b",
                str(tmp_png),
                "--save-as", str(output_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=45)
            return proc.returncode == 0
        except asyncio.TimeoutError:
            return False
        except Exception:
            return False


async def convert_all_formats(tmp_png: Path) -> int:
    """Smart format scheduling: fast formats first."""
    fast_tasks = [convert_png_to_format(tmp_png, fmt) for fmt in FAST_FORMATS]
    slow_tasks = [convert_png_to_format(tmp_png, fmt) for fmt in SLOW_FORMATS]

    fast_results = await asyncio.gather(*fast_tasks)
    slow_results = await asyncio.gather(*slow_tasks)

    return sum(fast_results) + sum(slow_results)


async def process_theme_batch(theme_dir: Path) -> list[tuple[str, str, int]]:
    """Process all flags for a theme in one batch."""
    svg_paths = [
        theme_dir / flag_key / f"{flag_key}.svg"
        for flag_key in flags_to_process
        if (theme_dir / flag_key / f"{flag_key}.svg").exists()
    ]

    if not svg_paths:
        return [(fk, theme_dir.name, 0) for fk in flags_to_process]

    # SVG rendering (I/O-bound, can be aggressive)
    async with SVG_SEMAPHORE:
        png_map = await export_svgs_batch(svg_paths)

    results = []
    for svg_path, tmp_png in png_map.items():
        flag_key = svg_path.parent.name
        if not tmp_png:
            results.append((flag_key, theme_dir.name, 0))
            continue

        # Format conversion (CPU-bound, serialized per-flag)
        success_count = await convert_all_formats(tmp_png)
        tmp_png.unlink()
        results.append((flag_key, theme_dir.name, success_count))

    return results


async def main() -> None:
    tasks = [process_theme_batch(theme_dir) for theme_dir in THEME_DIRS]

    all_results = []
    for coro in tqdm.as_completed(tasks, total=len(tasks), desc="Processing"):
        batch_results = await coro
        all_results.extend(batch_results)

        for flag_key, theme_name, success_count in batch_results:
            status = "✓" if success_count > 0 else "✗"
            print(f"{status} {flag_key}/{theme_name}: {success_count}/{len(FAST_FORMATS) + len(SLOW_FORMATS)} formats")

    print(f"\n✓ All files exported via {TOOL}.")


if __name__ == "__main__":
    try:
        import uvloop
        asyncio.run(main(), loop_factory=uvloop.new_event_loop)
    except ImportError:
        asyncio.run(main())
