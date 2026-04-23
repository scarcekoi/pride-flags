setup := "source venv/bin/activate && pip install -r requirements.txt --upgrade"

templates:
    {{ setup }}
    python scripts/build.py templates

export:
    {{ setup }}
    python scripts/build.py export

composite:
    {{ setup }}
    python scripts/build.py composite

optimize:
    {{ setup }}
    python scripts/build.py optimize

readme:
    {{ setup }}
    python scripts/build.py readme

package:
    {{ setup }}
    python scripts/build.py package

[default]
all:
    {{ setup }}
    python scripts/build.py all
