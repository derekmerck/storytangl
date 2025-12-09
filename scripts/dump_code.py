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
docs_root = project_root / "docs"
apps_root = project_root / "apps"
tests_root = project_root / "engine/tests"
legacy_root = project_root / "scratch/legacy"
scratch_root = project_root / "scratch"

cwx_root = project_root.parent / "carwars-gamebooks/carwars"

outfile_dir = project_root / "tmp/dumps"

def get_tree(root: Path, include_notes: bool = False):

    if not include_notes:
        pattern = "*.py"
    else:
        pattern = "*.py|*.md|*.rst"
    result = subprocess.run(["tree", "-P", pattern, "-I", "__pycache__", "--charset=ascii"],
                            capture_output=True,
                            text=True,
                            cwd=root.absolute()
                            ).stdout
    return result

def process_directory(root: Path,
                      outfile_name: str,
                      include_notes: bool = False,
                      prepend_files: list[Path] = None,
                      postpend_files: list[Path] = None):

    print( root )
    data = {}
    files = list(root.glob("**/*.py"))  # + list(root.glob("**/*.md"))
    # print( files )
    if include_notes:
        files = files + list(root.glob("**/*.md"))
        files = files + list(root.glob("**/*.yaml"))
        files = files + list(root.glob("**/*.rst"))
    if prepend_files is not None:
        files = prepend_files + files
    if postpend_files is not None:
        files = files + postpend_files
    for f in files:
        with open(f) as fp:
            try:
                name = f.relative_to(root)
            except ValueError:
                try:
                    name = f.relative_to(pkg_root)
                except ValueError:
                    try:
                        name = f.relative_to(project_root)
                    except:
                        name = f
            content = fp.read()
            if f.suffix in [".md", ".csv", ".txt", ".json", ".rst", ".yaml"]:
                content = "'''\n" + content + "'''\n"
                match f.suffix:
                    case ".md":
                        content = '# language=markdown\n' + content
                    case ".rst":
                        content = '# language=rst\n' + content
                    case ".yaml":
                        content = '# language=yaml\n' + content
            if content:
                data[name] = content

    tree = get_tree(root, include_notes=include_notes)

    content_hash = hashlib.sha224(str(data.values()).encode("utf8")).digest()
    content_hash_b64 = b64encode(content_hash).decode("utf8").strip("=")

    def _fp(fn):
        try:
            result = Path(fn).relative_to(project_root)
            for p in ['engine/src/', 'engine/tests/', 'scratch/legacy/']:
                if p in str(result):
                    result = result.relative_to(p)
            return result
        except ValueError:
            return fn

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
    process_directory(pkg_root,
                      "tangl37_full_archive.py",
                      include_notes=False)
    process_directory(pkg_root / "core",
                      "tangl37_core_archive.py",
                      include_notes=True,
                      prepend_files= [pkg_root / "type_hints.py",
                                      pkg_root / "info.py"],
                      postpend_files=[pkg_root / "utils/base_model_plus.py"])
    process_directory(pkg_root / "vm",
                      "tangl37_vm_archive.py",
                      include_notes=True,
                      postpend_files=[pkg_root / "utils/hashing.py"])
    process_directory(pkg_root / 'service', "tangl37_service_archive.py")
    process_directory(pkg_root / 'story',
                      "tangl37_story_archive.py",
                      include_notes=True)
    process_directory(pkg_root / 'story/fabula',
                      "tangl37_fabula_archive.py",
                      include_notes=True)
    process_directory(pkg_root / 'ir', "tangl37_ir_archive.py")
    process_directory(pkg_root / 'journal', "tangl37_journal_archive.py")

    process_directory(apps_root / "server/src/tangl/rest",
                      "tangl37_server_archive.py",
                      include_notes=True)

    process_directory(apps_root / "cli/src/tangl/cli",
                      "tangl37_cli_archive.py",
                      include_notes=True,
                      postpend_files=[
                          tests_root / "resources/demo_script.yaml",
                          apps_root / "cli/tests/test_story_cli_integration.py"])

    process_directory(pkg_root / 'lang', "tangl37_lang_archive.py",
                      postpend_files=[pkg_root / "lang/pos/treebank-symbols.csv",
                                      pkg_root / "lang/pos/treebank_symbols.pyi"])
    process_directory(pkg_root / 'persistence', "tangl37_persist_archive.py")
    process_directory(pkg_root / 'utils', "tangl37_utils_archive.py")

    process_directory(pkg_root / 'mechanics', "tangl3x_mechanics_snippits.py", include_notes=True)
    process_directory(pkg_root / 'media', "tangl3x_media_snippits.py", include_notes=True)

    process_directory(docs_root / "src", "tangl37_docs_archive.py", include_notes=True)
    process_directory(docs_root / "build/markdown", "tangl37_md_docs_archive.py", include_notes=True)

    # testing
    process_directory(tests_root, "tangl37_tests_archive.py")
    process_directory(tests_root / 'core', "tangl37_core_tests_archive.py")
    process_directory(tests_root / 'vm',   "tangl37_vm_tests_archive.py")
    process_directory(tests_root / 'service',   "tangl37_service_tests_archive.py")
    process_directory(tests_root / 'story',   "tangl37_story_tests_archive.py")

    process_directory(tests_root / 'lang',   "tangl37_lang_tests_archive.py")
    process_directory(tests_root / 'persistence',   "tangl37_persist_tests_archive.py")
    process_directory(tests_root / 'utils',   "tangl37_utils_tests_archive.py")

    # legacy
    process_directory(legacy_root / "core/core-34", "tangl34_core_archive.py")
    process_directory(legacy_root / "vm/vm-34",     "tangl34_vm_archive.py")
    process_directory(legacy_root / "core/core-35", "tangl35_core_archive.py")
    process_directory(legacy_root / "core/core-36", "tangl36_core_archive.py")
    # process_directory(legacy_root / "vm/vm-36",     "tangl36_vm_archive.py")

    process_directory(scratch_root / "mechanics/progression", "tangl3x_progression_archive.py", include_notes=True)
    process_directory(scratch_root / "mechanics/presence", "tangl3x_presence_archive.py", include_notes=True)
    process_directory(scratch_root / "old/docs", "tanglxx_docs_archive.py", include_notes=True)

    process_directory(cwx_root / "domain", "tangl2x_cwx_archive.py",
                      prepend_files=[cwx_root / 'world.yaml'])
