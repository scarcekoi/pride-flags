# Contributing!

🎉 First off, thanks for taking the time to contribute! 🎉

> [!IMPORTANT]
> The regenerate data action currently does not work. Any help to fix it is much appreciated.

## Guidelines

The following is a set of guidelines for contributing to this repository. Use your best judgment, and feel free to propose
changes to this document in a pull request.

- Use the `.editorconfig` file (located at the root of this project) on your editor to "maintain consistent coding
  styles." For instructions on how to use this file refer to [EditorConfig's website](https://editorconfig.org/).
- Use [conventionalcommits.org](https://www.conventionalcommits.org/en/v1.0.0/)'s rules for creating explicit
  and meaningful commit messages.

## Recommendations

- Create a [topic branch](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows#_topic_branch) on your fork for your
  specific PR. 
- Consider using [conventionalcommits.org](https://www.conventionalcommits.org/en/v1.0.0/)'s rules for creating explicit
  and meaningful commit messages.

## Prerequisites

- Install [Inkscape](https://inkscape.org) to generate SVG files from template files.
- Install [Python](https://python.org) to run the scripts.
- Install [Whiskers](https://whiskers.catppuccin.com) to write and use TERA template files.

## Scripts

After you create/edit a template file, run `./scripts/whiskers-run.sh` to generate the corresponding SVG files from that template.
Then run `./scripts/create-files.py` to generate the rest of the files from the SVG files.
Then run `./scripts/catwalk-run.sh` to generate the preview images from the SVG files.
Run `./scripts/update-flaglist.py` and `./scripts/update-previews.py` to update the README flaglist and previews. This is only necessary if you've added or removed a flag.
