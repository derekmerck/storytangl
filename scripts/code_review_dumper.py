"""
Utility for collating subpackages into a unified doc for review

Optionally minifying with python-minify will reduce the token count about 20%,
even while preserving docstrings (preserve literals).  However, it may prompt
a lot of bellyaching from the review agent about formatting.
"""

from pathlib import Path
import os
import re

Pathlike = str | Path

# COLLECTION = [ "full", "test" ]

# name: ([ include ], [ ignore ] )
BASE_DIR = Path(__file__).parent.parent
PKG_NAME = "tangl"

collections = {
    "full": ([PKG_NAME], []),
    # # core only
    # "core": ([f"{PKG_NAME}/core"], []),
    # # story only
    # "story": ([f"{PKG_NAME}/business/story"], []),
    # # media only
    # "media": ([f"{PKG_NAME}/business/content/media"], []),
    # # service only
    # "service": ([f"{PKG_NAME}/service"], []),
    # tests only
    "tests": ([f"tests"], []),
    # overview only
    "overview": ([f"scratch/overview"], [])
}

file_exts = [".py", ".toml", ".md", ".rst"]

MINIFY = False
STRIP = True

if MINIFY:
    try:
        from python_minifier import minify
    except ImportError:
        print("Disabling minification")
        MINIFY = False

def write_file_strings(file_strings: list[str], outfile: Pathlike):
    with open(outfile, 'w') as f:
        for file_string in file_strings:
            f.write(file_string)

def get_file_strings(root_dir):
    all_file_strings = []
    for subdir, dirs, files in os.walk(root_dir):
        if any( [ subdir.find( x ) >= 0 for x in ignore ] ):
            continue
        for file in sorted(files):
            if any( [ file.find( x ) >= 0 for x in ignore ] ):
                continue
            if any([file.endswith(ext) for ext in file_exts]):
                filepath = subdir + os.sep + file
                relative_fp = Path( filepath ).relative_to( root_dir )

                with open(filepath) as f:
                    print(f"trying to read {filepath}")
                    data = f.read()

                data = re.sub(r"<!--.*-->", "", data, flags=re.DOTALL)

                if STRIP and filepath.endswith(".py"):
                    data = data.splitlines()
                    data = list(filter(lambda v: bool(v) and not re.match(r"^ *#", v), data))
                    data = list(filter(lambda v: bool(v) and not re.match(r"^ *logger\.debug", v), data))
                    data = list(filter(lambda v: bool(v) and not re.match(r"^ *(from|import)\b", v), data))
                    data = list(filter(lambda v: bool(v) and not re.match(r"^ *(if TYPE_CHECKING:)", v), data))

                    if not data:
                        continue
                    data = "\n".join(data)

                if MINIFY:
                    data = minify(data)

                if filepath.endswith(".toml") or filepath.endswith(".md"):
                    data = '"""\n' + data + '"""\n'

                header = f"# {'Minified' if MINIFY else ''} File: {relative_fp}\n"
                footer = "\n\n# --- End of " + file + " ---\n\n"

                data = header + data + footer
                all_file_strings.append( data )

    return all_file_strings

import subprocess

def run_tree_command(directory: str) -> str:
    try:
        # Run the tree command and capture the output
        cmd = f"cd .. && git ls-tree -r --name-only HEAD:{directory} | tree --fromfile --charset=ascii --dirsfirst"
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running tree command: {e}")
        return ""


import re

def convert_coverage_to_relative_paths(report):
    lines = report.split('\n')
    lines.pop()  # there's a blank line at the end
    processed_lines = []
    path_pattern = re.compile(r'^\/.*?\/(afc\/.*)$')  # Pattern to capture everything after '/afc'

    # Find the first line with a path to determine the prefix to remove
    for line in lines:
        match = path_pattern.match(line)
        if match:
            # Determine the length of the prefix to remove
            useful_path = match.group(1)
            prefix_length = len(line) - len(useful_path)
            break
    else:
        raise ValueError("No matching paths found in the report")

    # Process the header line and adjust the spaces
    header_line = lines[0]
    adjusted_header = "Name" + header_line[prefix_length+4:]
    processed_lines.append(adjusted_header)

    # Process the dashed line
    dashed_line = lines[1]
    adjusted_dashed_line = dashed_line[prefix_length:]
    processed_lines.append(adjusted_dashed_line)

    # Process each remaining line
    for line in lines[2:-2]:
        match = path_pattern.match(line)
        if match:
            relative_path = match.group(1)
            processed_lines.append(relative_path)
        else:
            processed_lines.append(line)

    # Process the footer lines and adjust the spaces
    processed_lines[-2] = lines[-2][prefix_length:]
    processed_lines[-1] = lines[-1][prefix_length:]

    return '\n'.join(processed_lines)


def run_coverage_report() -> str:
    try:
        cmd = f"cd .. && coverage report"
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
        report = result.stdout
        return report
        # return convert_coverage_to_relative_paths(report)
    except subprocess.CalledProcessError as e:
        print(f"Error running coverage command: {e}")
        return ""


if __name__ == "__main__":

    for c in collections:
        root_dirs, ignore = collections[c]
        if c.find("docs") > -1:
            file_ext = "rst"
        else:
            file_ext = "py"

        output_file = f"../tmp/dumps/{c}-dump.{file_ext}"
        run_once = False

        file_strings = []
        for root_dir in root_dirs:

            if root_dir.startswith("../"):
                data = run_tree_command(root_dir[3:])
            #
            # if root_dir.startswith("../docs"):
            #     data = run_tree_command("docs")
            # elif root_dir.startswith("../clients/cli/afc"):
            #     data = run_tree_command("clients/cli/afc")
            # elif root_dir.startswith("../server/afc"):
            #     data = run_tree_command("server/afc")
            else:
                data = run_tree_command(root_dir)
            header = f'# Tree: {root_dir}\n"""\n'
            footer = '\n"""\n# --- End of tree ---\n\n'
            data = header + data + footer
            file_strings.append( data )

            if not run_once and c in ["test"]:
                run_once = True
                data = run_coverage_report()
                header = f'# Coverage\n"""\n'
                footer = '\n"""\n# --- End of coverage ---\n\n'
                data = header + data + footer
                file_strings.append( data )

            file_strings.extend( get_file_strings( BASE_DIR / root_dir ) )

        write_file_strings(file_strings, output_file)
