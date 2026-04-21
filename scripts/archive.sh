#!/bin/env bash

mkdir -p 'dist/release/flags'
mkdir -p 'dist/release/flavours'

THEMES=(mocha macchiato frappe latte)

# Create theme archives (mocha.zip, etc.)
for theme in "${THEMES[@]}"; do
    tar -I 'xz -T0 -c -z --best -' -cf "dist/release/flavours/${theme}.tar.xz" "themes/${theme}/"*
    echo "Created theme archive: dist/release/flavours/${theme}.tar.xz"
done

# Read flags from resources/flags.yml
FLAGS=$(yq -r '.flags | keys[]' resources/flags.yml)

# Create flag archives (transgender.zip, etc.)
for flag in $FLAGS; do
    TARBALL="dist/release/flags/${flag}.tar.xz"
    rm -f "${TARBALL}"

    for theme in "${THEMES[@]}"; do
        THEME_FLAG_DIR="themes/${theme}/${flag}"
        if [[ -d "$THEME_FLAG_DIR" ]]; then
            # Add the flag folder under the theme folder inside the zip
            tar -I 'xz -T0 -c -z --best -' --exclude '.*' -cf "${TARBALL}" "${THEME_FLAG_DIR}"
        fi
    done
  echo "Created flag archive: ${TARBALL}"
done
