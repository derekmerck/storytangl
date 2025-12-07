"""
$ FLASK_APP=tangl.rest.__main__:app python -m flask run
"""

from legacy.rest.app import create_app
from tangl.world import World

THREADING = False

World.load_all()
for k in World.ls():
    print(f"   -> Found {World[k].label}")
print()

app = create_app()

def main():  # pragma: no cover
    print(f" * Threading {'enabled' and THREADING or 'disabled'}")
    app.run(port=5000, threaded=THREADING)


if __name__ == "__main__":  # pragma: no cover
    main()
