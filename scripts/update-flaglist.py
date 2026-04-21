#!/usr/bin/env python3
"""Generate flag list section in README from YAML metadata."""

import re
import yaml

from pathlib import Path

FLAGS_FILE = Path("./resources/flags.yml")
CATEGORIES_FILE = Path("./resources/categories.yml")
README_FILE = Path("./README.md")


def main() -> None:
    with FLAGS_FILE.open("r") as f:
        flags_data = yaml.safe_load(f)
    with CATEGORIES_FILE.open("r") as f:
        categories_data = yaml.safe_load(f)

    flags = flags_data.get("flags", {})

    cat_flags: dict[str, list[tuple[str, str]]] = {
        cat["key"]: [] for cat in categories_data
    }
    for flag_key, flag_info in flags.items():
        for cat in flag_info.get("categories", []):
            if cat in cat_flags:
                cat_flags[cat].append((flag_key, flag_info["name"]))

    # Sort once per category
    for cat in cat_flags:
        cat_flags[cat].sort(key=lambda x: x[1])

    lines = [
        "<!-- AUTOGEN:FLAGLIST START -->",
        "<!-- the following section is auto-generated, do not edit -->\n",
    ]

    for category in categories_data:
        key = category["key"]
        name = category["name"]

        if not cat_flags[key]:
            continue

        lines.append("<details closed>")
        lines.append(f"<summary>{name}</summary>\n")

        for flag_key, flag_name in cat_flags[key]:
            themes = ", ".join(
                f"[{t.title()}](themes/{t}/{flag_key}/)"
                for t in ("mocha", "macchiato", "frappé", "latte")
            )
            lines.append(f"- {flag_name} ({themes})")

        lines.append("\n</details>\n")

    lines.append("<!-- AUTOGEN:FLAGLIST END -->")

    readme_text = README_FILE.read_text()
    updated_text = re.sub(
        r"<!-- AUTOGEN:FLAGLIST START -->.*?<!-- AUTOGEN:FLAGLIST END -->",
        "\n".join(lines),
        readme_text,
        flags=re.DOTALL,
    )

    README_FILE.write_text(updated_text)
    print("✓ Flags section updated.")


if __name__ == "__main__":
    main()
