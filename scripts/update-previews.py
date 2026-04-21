#!/usr/bin/env python3

import re
import yaml

from pathlib import Path
from io import StringIO

flags_file = Path("./resources/flags.yml")
readme_file = Path("./README.md")

with flags_file.open("r") as f:
    flags_data = yaml.safe_load(f)

sorted_flags = sorted(
    flags_data.get("flags", {}).items(),
    key=lambda x: x[1]["name"].lower()
)


def generate_preview_section() -> str:
    buf = StringIO()
    buf.write("<!-- AUTOGEN:PREVIEWS START -->\n")
    buf.write("<!-- the following section is auto-generated, please edit scripts/update-previews.py to change this. -->\n\n")

    for flag_key, flag_info in sorted_flags:
        flag_name = flag_info["name"]
        buf.write(
            f"<details closed>\n"
            f"<summary>{flag_name}</summary>\n"
            f'<img src="assets/composite/{flag_key}.webp" alt="{flag_name} composite" style="width:50%;"/>\n'
            f'<img src="assets/grid/{flag_key}.webp" alt="{flag_name} grid" style="width:50%;"/>\n'
            f'<img src="assets/row/{flag_key}.webp" alt="{flag_name} row" style="width:50%;"/>\n'
            f"</details>\n\n"
        )

    buf.write("<!-- AUTOGEN:PREVIEWS END -->")
    return buf.getvalue()


new_section = generate_preview_section()
readme_text = readme_file.read_text()
updated_text = re.sub(
    r"<!-- AUTOGEN:PREVIEWS START -->.*?<!-- AUTOGEN:PREVIEWS END -->",
    new_section,
    readme_text,
    flags=re.DOTALL,
)
readme_file.write_text(updated_text)

print(":3 Previews section updated (500 entries).")
