import re
from pathlib import Path

import yaml

flags_file = Path("./resources/flags.yml")
readme_file = Path("./README.md")

with flags_file.open("r") as f:
    flags_data = yaml.safe_load(f)

# Sort flags alphabetically by name
sorted_flags = sorted(
    flags_data.get("flags", {}).items(), key=lambda x: x[1]["name"].lower()
)

lines = []
lines.append("<!-- AUTOGEN:PREVIEWS START -->")
lines.append("<!-- the following section is auto-generated, do not edit -->\n")

for flag_key, flag_info in sorted_flags:
    flag_name = flag_info["name"]
    lines.append(f"<details closed>")
    lines.append(f"<summary>{flag_name}</summary>\n")
    lines.append(
        f'<img src="assets/composite/{flag_key}.webp" alt="{flag_name} composite" style="width:50%;"/>'
    )
    lines.append(
        f'<img src="assets/grid/{flag_key}.webp" alt="{flag_name} grid" style="width:50%;"/>'
    )
    lines.append(
        f'<img src="assets/row/{flag_key}.webp" alt="{flag_name} row" style="width:50%;"/>'
    )
    lines.append("\n</details>\n")

lines.append("<!-- AUTOGEN:PREVIEWS END -->")

new_section = "\n".join(lines)

readme_text = readme_file.read_text()
updated_text = re.sub(
    r"<!-- AUTOGEN:PREVIEWS START -->.*?<!-- AUTOGEN:PREVIEWS END -->",
    new_section,
    readme_text,
    flags=re.DOTALL,
)

readme_file.write_text(updated_text)
print("Previews section updated.")
