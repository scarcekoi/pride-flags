#!/usr/bin/env bash

mkdir -p 'dist/release/flags'
mkdir -p 'dist/release/flavours'

THEMES=(mocha macchiato frappe latte)

# Create theme archives (mocha.zip, etc.)
for theme in "${THEMES[@]}"; do
  tar -I 'xz -T0 -c -z --best -' -cf "dist/release/flavours/${theme}.tar.xz" "themes/${theme}/"*
  echo "Created theme archive: dist/release/flavours/${theme}.tar.xz"
done

# Read flags with parent dirs from resources/flags.yml
python3 - <<'PYTHON' >/tmp/flags_with_parents.txt
import yaml
with open("resources/flags.yml") as f:
    data = yaml.safe_load(f)
flags = data.get("flags", {})
for flag_name, flag_config in flags.items():
    if isinstance(flag_config, dict):
        parent = flag_config.get("parent", flag_name)
    else:
        parent = flag_name
    print(f"{flag_name}:{parent}")
PYTHON

# Create flag archives (transgender.zip, etc.)
while IFS=: read -r flag parent; do
  TARBALL="dist/release/flags/${flag}.tar.xz"
  rm -f "${TARBALL}"

  for theme in "${THEMES[@]}"; do
    THEME_FLAG_DIR="themes/${theme}/${parent}/${flag}"
    if [[ -d "$THEME_FLAG_DIR" ]]; then
      tar -I 'xz -T0 -c -z --best -' --exclude '.*' -cf "${TARBALL}" "${THEME_FLAG_DIR}"
    fi
  done
  echo "Created flag archive: ${TARBALL}"
done </tmp/flags_with_parents.txt
