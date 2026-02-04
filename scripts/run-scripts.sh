#!/bin/sh

./scripts/whiskers-run.sh
./scripts/create-files.py all
./scripts/catwalk-run.sh
./scripts/update-flaglist.py
./scripts/update-previews.py
