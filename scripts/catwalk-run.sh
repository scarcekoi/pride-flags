#!/bin/sh
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
FLAGS_FILE="$SCRIPT_DIR/../resources/flags.yml"

FLAGS=$(python3 - <<PYTHON
import yaml
with open("$FLAGS_FILE") as f:
    data = yaml.safe_load(f)
flags = data.get("flags", {})
print(" ".join(flags.keys()))
PYTHON
)

LAYOUTS="composite grid row"

for flag in $FLAGS; do
    for layout in $LAYOUTS; do
        catwalk \
            "themes/latte/$flag/$flag.webp" \
            "themes/frappe/$flag/$flag.webp" \
            "themes/macchiato/$flag/$flag.webp" \
            "themes/mocha/$flag/$flag.webp" \
            -o "assets/$layout/$flag.webp" \
            -l "$layout" -r 0
    done
done
