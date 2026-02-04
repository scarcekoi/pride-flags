#!/bin/sh
find . -type f -name '*.tera' -exec whiskers {} \;
