#!/usr/bin/env bash

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
FLAGS_FILE="$SCRIPT_DIR/../resources/flags.yml"

FLAGS_CACHE="/tmp/flags_cache.txt"
rm $FLAGS_CACHE

python3 - <<PYTHON >"$FLAGS_CACHE"
import yaml
with open("$FLAGS_FILE") as f:
    data = yaml.safe_load(f)
flags = data.get("flags", {})
for flag_name, flag_config in flags.items():
    # Get parent dir if defined, otherwise use flag name
    if isinstance(flag_config, dict):
        dir_name = flag_config.get("parent", flag_name)
    else:
        dir_name = flag_name
    print(f"{flag_name}:{dir_name}")
PYTHON

FLAGS=$(cat "$FLAGS_CACHE")
LAYOUTS="composite grid row"

for flag_with_dir in $FLAGS; do
  flag="${flag_with_dir%:*}"
  dir="${flag_with_dir#*:}"
  for layout in $LAYOUTS; do
    printf '%s\0%s\0%s\0' "$flag" "$layout" "$dir"
  done
done | xargs -0 -P 8 -n 3 bash -c '
flag=$1
layout=$2
dir=$3
catwalk \
    "themes/latte/$dir/$flag.webp" \
    "themes/frappe/$dir/$flag.webp" \
    "themes/macchiato/$dir/$flag.webp" \
    "themes/mocha/$dir/$flag.webp" \
    -o "assets/$layout/$flag.webp" \
    -l "$layout" -r 0
' _
