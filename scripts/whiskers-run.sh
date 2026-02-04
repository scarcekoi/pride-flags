#!/bin/sh
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
find "$SCRIPT_DIR/../templates" -type f -name '*.tera' -exec whiskers {} \;
