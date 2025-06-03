"""
Invoke with:

```
$ python -m tangl.cli
```
"""
import logging

from tangl.cli.app import app

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)

def main():
    app.cmdloop()


if __name__ == '__main__':
    main()
