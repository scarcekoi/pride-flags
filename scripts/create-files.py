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

formats = [
    "ase",
    "aseprite",
    "bmp",
    "css",
    "flc",
    "fli",
    "jpeg",
    "jpg",
    "pcx",
    "pcc",
    "png",
    "qoi",
    "tga",
    "webp",
]

for flag_key in flags_to_process:
    for theme_dir in themes_dir.iterdir():
        if not theme_dir.is_dir():
            continue

        svg_path = theme_dir / flag_key / f"{flag_key}.svg"
        if not svg_path.exists():
            print(f"SVG not found: {svg_path}")
            continue

        tmp_png = svg_path.with_suffix(".tmp.png")
        # Export a temporary PNG from SVG
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

        for fmt in formats:
            output_path = svg_path.with_suffix(f".{fmt}")
            subprocess.run(
                ["aseprite", "-b", str(tmp_png), "--save-as", str(output_path)],
                check=True,
            )

        tmp_png.unlink()

print("All files exported at maximum quality via Aseprite.")
