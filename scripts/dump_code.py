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
legacy_root = project_root / "scratch/legacy"
outfile_dir = project_root / "tmp/dumps"

def get_tree(root: Path):

    result = subprocess.run(["tree", "-P", "*.py", "-I", "__pycache__", "--charset=ascii"],
                            capture_output=True,
                            text=True,
                            cwd=root.absolute()
                            ).stdout
    return result

def process_directory(root: Path,
                      outfile_name: str,
                      include_mds: bool = False,
                      prepend_files: list[Path] = None,
                      postpend_files: list[Path] = None):

    print( root )
    data = {}
    files = list(root.glob("**/*.py"))  # + list(root.glob("**/*.md"))
    if include_mds:
        files = files + list(root.glob("**/*.md"))
    if prepend_files is not None:
        files = prepend_files + files
    if postpend_files is not None:
        files = files + postpend_files
    for f in files:
        with open(f) as fp:
            try:
                name = f.relative_to(root)
            except ValueError:
                name = f.relative_to(pkg_root)
            content = fp.read()
            if f.suffix == ".md":
                content = '"""\n' + content + '"""\n'
            if content:
                data[name] = content

    tree = get_tree(root)

    content_hash = hashlib.sha224(str(data.values()).encode("utf8")).digest()
    content_hash_b64 = b64encode(content_hash).decode("utf8").strip("=")

    def _fp(fn):
        result = Path(fn).relative_to(project_root)
        for p in ['engine/src/', 'engine/tests/', 'scratch/legacy/']:
            if p in str(result):
                result = result.relative_to(p)
        return result

        # if 'engine/src/' in str(result):
        #     result = result.relative_to('engine/src/')
        # elif 'engine/tests/' in str(result):
        #     result = result.relative_to('engine/tests/')
        # elif 'scratch/legacy/' in str(result):
        #     result = result.relative_to('scratch/legacy/')
        # return result

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
        if ignore_imports:
            v = re.sub(r"^[^\n]*(?:from [\w.]+? )?import .+?\n", "", v, flags=re.MULTILINE)
            # s = re.sub(r"^\W*from [\w.]+? import .+?\n", "", s, flags=re.MULTILINE)
            v = re.sub(r"if TYPE_CHECKING:", "", v)
        # get rid of file name comments
        v = re.sub(r"^# [Tt]angl[/.].*\n+", "", v, flags=re.MULTILINE)

        if not re.findall(r'\w', v):
            # discard empty init files
            print(f"Skipping {k}")
            continue

        s += _start_f(k)
        s += v
        s += _end_f(k)

    # collapse multiple newlines to a double newline
    s = re.sub(r'\n{2,}', "\n\n", s)
    # get rid of leading newline
    s = s.lstrip("\n")
    # print(s)

    outfile = outfile_dir / outfile_name
    with outfile.open("w") as fp:
        fp.write(s)


if __name__ == "__main__":
    # current
    process_directory(pkg_root / "core",
                      "tangl37_core_archive.py",
                      include_mds=True,
                      prepend_files= [pkg_root / "type_hints.py",
                                      pkg_root / "info.py"],
                      postpend_files=[pkg_root / "utils/base_model_plus.py"])
    process_directory(pkg_root / "vm",
                      "tangl37_vm_archive.py",
                      include_mds=True,
                      postpend_files=[pkg_root / "utils/hashing.py"])

    process_directory(pkg_root / 'persistence', "tangl37_persist_archive.py")
    process_directory(pkg_root / 'utils', "tangl37_utils_archive.py")

    process_directory(pkg_root / 'story', "tangl3x_story_snippits.py", include_mds=True)
    process_directory(pkg_root / 'mechanics', "tangl3x_mechanics_snippits.py", include_mds=True)
    process_directory(pkg_root / 'media', "tangl3x_media_snippits.py", include_mds=True)

    # testing
    process_directory(tests_root / 'core', "tangl37_core_tests_archive.py")
    process_directory(tests_root / 'vm',   "tangl37_vm_tests_archive.py")
    process_directory(tests_root / 'persistence',   "tangl37_persist_tests_archive.py")
    process_directory(tests_root / 'utils',   "tangl37_utils_tests_archive.py")

    # legacy
    process_directory(legacy_root / "core/core-34", "tangl34_core_archive.py")
    process_directory(legacy_root / "vm/vm-34",     "tangl34_vm_archive.py")
    process_directory(legacy_root / "core/core-35", "tangl35_core_archive.py")
    process_directory(legacy_root / "core/core-36", "tangl36_core_archive.py")
    process_directory(legacy_root / "vm/vm-36",     "tangl36_vm_archive.py")
