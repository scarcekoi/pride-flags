#!/bin/bash

JOBS=$(($(nproc) - 2))

# Process all files in one parallel job pool
{
  find . -type f -name "*.png" -exec echo "optipng -o7 -zm1-9 -strip all -fix -preserve -clobber -quiet {}" \;
  find . -type f -name "*.svg" -exec echo "svgo --multipass {}" \;
  find . -type f -regex ".*\.jpe?g" -exec echo "jpegoptim -s -- {}" \;
  find . -type f -name "*.gif" -exec echo "gifsicle --batch --optimize {}" \;
} | parallel -j${JOBS}
