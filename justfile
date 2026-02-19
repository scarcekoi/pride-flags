_default:
    @just --list

do-everything: whiskers create-files catwalk update-flaglist update-previews optimise

whiskers:
    ./scripts/whiskers-run.sh

create-files:
    ./scripts/create-files.py all

catwalk:
    ./scripts/catwalk-run.sh

update-flaglist:
    ./scripts/update-flaglist.py all

update-previews:
    ./scripts/update-previews.py

optimise:
    ./scripts/optimise.sh

archive:
    ./scripts/archive.sh
