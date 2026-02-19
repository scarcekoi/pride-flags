_default:
    @just --list

do-everything: build gen-files catwalk flaglist preview optimise

build:
    ./scripts/whiskers-run.sh

gen-files:
    ./scripts/create-files.py all

catwalk:
    ./scripts/catwalk-run.sh

flaglist:
    ./scripts/update-flaglist.py all

preview:
    ./scripts/update-previews.py

optimise:
    ./scripts/optimise.sh

