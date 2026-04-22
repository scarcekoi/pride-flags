#!/bin/bash

JOBS=$(($(nproc) - 2))

# PNG files
find . -type f -name "*.png" -print0 |
  parallel -0 -j${JOBS} 'optipng -o7 -zm1-9 -strip all -fix -preserve -clobber -quiet {} && echo "Processed: {}"'

# SVG files
find . -type f -name "*.svg" -print0 |
  parallel -0 -j${JOBS} 'svgo --quiet --multipass {} && echo "Processed: {}"'

# JPG/JPEG files
find . -type f \( -name "*.jpg" -o -name "*.jpeg" \) -print0 |
  parallel -0 -j${JOBS} 'jpegoptim --quiet -s -- {} && echo "Processed: {}"'
