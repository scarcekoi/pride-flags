setup := "./venv/bin/python -m pip install -r requirements.txt --upgrade && ./venv/bin/python -m playwright install chromium"

templates:
    {{ setup }}
    ./venv/bin/python scripts/build.py templates

export:
    {{ setup }}
    ./venv/bin/python scripts/build.py export

composite:
    {{ setup }}
    ./venv/bin/python scripts/build.py composite

optimize:
    {{ setup }}
    ./venv/bin/python scripts/build.py optimize

readme:
    {{ setup }}
    ./venv/bin/python scripts/build.py readme

package:
    {{ setup }}
    ./venv/bin/python scripts/build.py package

[default]
all:
    {{ setup }}
    ./venv/bin/python scripts/build.py all
