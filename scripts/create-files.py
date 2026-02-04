#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

import yaml

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

formats = ["png", "webp", "ase", "aseprite"]

for flag_key in flags_to_process:
    for theme_dir in themes_dir.iterdir():  # mocha, macchiato, frappe, latte
        if not theme_dir.is_dir():
            continue

        svg_path = theme_dir / flag_key / f"{flag_key}.svg"
        if not svg_path.exists():
            print(f"SVG not found: {svg_path}")
            continue

        for fmt in formats:
            output_path = svg_path.with_suffix(f".{fmt}")

            if fmt == "png":
                subprocess.run(
                    [
                        "inkscape",
                        str(svg_path),
                        "--export-type=png",
                        "--export-filename",
                        str(output_path),
                        "--export-background-opacity=0",
                    ],
                    check=True,
                )

            elif fmt == "webp":
                tmp_png = output_path.with_suffix(".tmp.png")
                subprocess.run(
                    [
                        "inkscape",
                        str(svg_path),
                        "--export-type=png",
                        "--export-filename",
                        str(tmp_png),
                        "--export-background-opacity=0",
                    ],
                    check=True,
                )
                subprocess.run(
                    ["cwebp", str(tmp_png), "-q", "100", "-o", str(output_path)],
                    check=True,
                )
                tmp_png.unlink()

            elif fmt in ["ase", "aseprite"]:
                tmp_png = output_path.with_suffix(".tmp.png")
                subprocess.run(
                    [
                        "inkscape",
                        str(svg_path),
                        "--export-type=png",
                        "--export-filename",
                        str(tmp_png),
                        "--export-background-opacity=0",
                    ],
                    check=True,
                )
                subprocess.run(
                    ["aseprite", "-b", str(tmp_png), "--save-as", str(output_path)],
                    check=True,
                )
                tmp_png.unlink()

print("All files exported at maximum quality.")
