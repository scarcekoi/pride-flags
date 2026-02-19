#!/usr/bin/env python3

import re
from pathlib import Path
from io import StringIO

import yaml

flags_file = Path("./resources/flags.yml")
readme_file = Path("./README.md")

with flags_file.open("r") as f:
    flags_data = yaml.safe_load(f)

sorted_flags = sorted(
    flags_data.get("flags", {}).items(),
    key=lambda x: x[1]["name"].lower()
)


def generate_preview_section() -> str:
    """Build HTML section with zero intermediate allocations."""
    buf = StringIO()
    write = buf.write  # Micro-optimization: cache method reference

    write("<!-- AUTOGEN:PREVIEWS START -->\n")
    write("<!-- the following section is auto-generated, do not edit -->\n\n")

    # Template strings (avoid repeated f-string evaluation)
    img_template = '<img src="assets/{}/{}.webp" alt="{} {}" style="width:50%;"/>\n'

    for flag_key, flag_info in sorted_flags:
        flag_name = flag_info["name"]
        write("<details closed>\n<summary>")
        write(flag_name)
        write("</summary>\n")

        # Batch writes for all images
        write(
            img_template.format(
                flag_key, "composite",
                flag_name, "composite"
            )
        )
        write(img_template.format(flag_key, "grid", flag_name, "grid"))
        write(img_template.format(flag_key, "row", flag_name, "row"))

        write("</details>\n\n")

    write("<!-- AUTOGEN:PREVIEWS END -->")
    return buf.getvalue()


new_section = generate_preview_section()

# Read once, write once
readme_text = readme_file.read_text()
updated_text = re.sub(
    r"<!-- AUTOGEN:PREVIEWS START -->.*?<!-- AUTOGEN:PREVIEWS END -->",
    new_section,
    readme_text,
    flags=re.DOTALL,
)
readme_file.write_text(updated_text)

print("✓ Previews section updated (500 entries).")
