"""
Creates single-file code archives of pkg and subpackages for review
"""
import hashlib
from pathlib import Path
import subprocess
import re
from base64 import b64encode
from datetime import datetime

exclude_patterns = []
ignore_imports = True

project_root = Path(__file__).parent.parent
pkg_root = project_root / "engine/src/tangl"
tests_root = project_root / "engine/tests"
outfile_dir = project_root / "tmp/dumps"

def get_tree(root: Path):

    result = subprocess.run(["tree", "-P", "*.py", "-I", "__pycache__", "--charset=ascii"],
                            capture_output=True,
                            text=True,
                            cwd=root.absolute()
                            ).stdout
    return result

def process_directory(root: Path, outfile_name: str):

    print( root )
    data = {}
    files = list(root.glob("**/*.py"))  # + list(root.glob("**/*.md"))
    for f in files:
        with open(f) as fp:
            name = f.relative_to(root)
            content = fp.read()
            if content:
                data[name] = content

    tree = get_tree(root)

    content_hash = hashlib.sha224(str(data.values()).encode("utf8")).digest()
    content_hash_b64 = b64encode(content_hash).decode("utf8").strip("=")

    def _fp(fn):
        result = Path(fn).relative_to(project_root)
        if 'engine/src/' in str(result):
            result = result.relative_to('engine/src/')
        return result

    def _marker(label: str):
        return f"\n# {'-'*10} {label} {'-'*10}\n"

    def _start_f(fn: str):
        return _marker(f'Start <{_fp(root)/fn}>')

    def _end_f(fn: str):
        return _marker(f'End <{_fp(root)/fn}>')

    s = ""

    s += _marker('Start content meta')
    s += '"""\n'
    s += f"timestamp: {datetime.now().isoformat(timespec="seconds")}\n"
    s += f"content digest: {content_hash_b64}\n"
    s += f"inspected files:\n{_fp(root)}\n"
    s += tree[2:]  # get rid of leading '.\n' line
    s += '"""\n'
    s += _marker('End content meta')

    for k, v in data.items():
        s += _start_f(k)
        s += v
        s += _end_f(k)

    if ignore_imports:
        s = re.sub(r"^[^\n]*(?:from [\w.]+? )?import .+?\n", "", s, flags=re.MULTILINE)
        # s = re.sub(r"^\W*from [\w.]+? import .+?\n", "", s, flags=re.MULTILINE)
    # get rid of file name comments
    s = re.sub(r"^# [Tt]angl[/.].*\n+", "", s, flags=re.MULTILINE)
    # collapse multiple newlines to a double newline
    s = re.sub(r'\n{2,}', "\n\n", s)
    # get rid of leading newline
    s = s.lstrip("\n")
    print(s)

    outfile = outfile_dir / outfile_name
    with outfile.open("w") as fp:
        fp.write(s)


if __name__ == "__main__":
    # process_directory(pkg_root, "tangl37_archive.py")
    process_directory(tests_root / 'v37',  "tangl37_tests_archive.py")
    process_directory(pkg_root / "core",   "tangl37_core_archive.py")
    process_directory(pkg_root / "vm",     "tangl37_vm_archive.py")

    process_directory(pkg_root / "core34", "tangl34_core_archive.py")
    process_directory(pkg_root / "vm34",   "tangl34_vm_archive.py")
    process_directory(pkg_root / "core36", "tangl36_core_archive.py")
    process_directory(pkg_root / "core35", "tangl35_core_archive.py")
