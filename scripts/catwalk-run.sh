#!/bin/env bash

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
FLAGS_FILE="$SCRIPT_DIR/../resources/flags.yml"

# Cache flags in a temp file (only re-parse if flags.yml changed)
FLAGS_CACHE="/tmp/flags_cache.txt"
if [ ! -f "$FLAGS_CACHE" ] || [ "$FLAGS_FILE" -nt "$FLAGS_CACHE" ]; then
    python3 - <<PYTHON > "$FLAGS_CACHE"
import yaml
with open("$FLAGS_FILE") as f:
    data = yaml.safe_load(f)
flags = data.get("flags", {})
print(" ".join(flags.keys()))
PYTHON
fi

FLAGS=$(cat "$FLAGS_CACHE")
LAYOUTS="composite grid row"

export_variant() {
    flag=$1
    layout=$2
    catwalk \
        "themes/latte/$flag/$flag.webp" \
        "themes/frappe/$flag/$flag.webp" \
        "themes/macchiato/$flag/$flag.webp" \
        "themes/mocha/$flag/$flag.webp" \
        -o "assets/$layout/$flag.webp" \
        -l "$layout" -r 0
}

export -f export_variant

# Generate all (flag, layout) combos with null delimiters
for flag in $FLAGS; do
    for layout in $LAYOUTS; do
        printf '%s\0%s\0' "$flag" "$layout"
    done
done | xargs -0 -P 8 -n 2 sh -c 'export_variant "$@"' _
