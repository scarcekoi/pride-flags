#!/usr/bin/env python3

import re
from pathlib import Path

import yaml

flags_file = Path("./resources/flags.yml")
categories_file = Path("./resources/categories.yml")
readme_file = Path("./README.md")

with flags_file.open("r") as f:
    flags_data = yaml.safe_load(f)

with categories_file.open("r") as f:
    categories_data = yaml.safe_load(f)

category_flags = {cat["key"]: [] for cat in categories_data}

for flag_key, flag_info in flags_data.get("flags", {}).items():
    for cat in flag_info.get("categories", []):
        if cat in category_flags:
            category_flags[cat].append(flag_info["name"])

for cat in category_flags:
    category_flags[cat].sort()

lines = []
lines.append("<!-- AUTOGEN:FLAGLIST START -->")
lines.append("<!-- the following section is auto-generated, do not edit -->\n")

for cat in categories_data:
    key = cat["key"]
    name = cat["name"]
    lines.append(f"<details closed>")
    lines.append(f"<summary>{name}</summary>\n")

    for flag_key, flag_info in flags_data.get("flags", {}).items():
        if key in flag_info.get("categories", []):
            flag_name = flag_info["name"]
            lines.append(
                f"- {flag_name} ([Mocha](themes/mocha/{flag_key}/), [Macchiato](themes/macchiato/{flag_key}/), [Frappé](themes/frappe/{flag_key}/), [Latte](themes/latte/{flag_key}/))"
                f"  - [Composite](assets/composite/{flag_key}.webp), [Grid](assets/grid/{flag_key}.webp), [Row](assets/row/{flag_key}.webp)"
            )

    lines.append("\n</details>\n")

lines.append("<!-- AUTOGEN:FLAGLIST END -->")

new_section = "\n".join(lines)

readme_text = readme_file.read_text()
updated_text = re.sub(
    r"<!-- AUTOGEN:FLAGLIST START -->.*?<!-- AUTOGEN:FLAGLIST END -->",
    new_section,
    readme_text,
    flags=re.DOTALL,
)

readme_file.write_text(updated_text)
print(f"Flags section updated.")
