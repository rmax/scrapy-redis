"""Print the HISTORY.rst section for a given version.

Used by the publish workflow to build the GitHub Release notes, so the
human-written changelog stays the single source of truth.

Usage: python .github/scripts/history_notes.py 0.10.0 [HISTORY.rst]
"""

import re
import sys

UNDERLINE = re.compile(r"^-{3,}\s*$")


def find_sections(lines):
    """Yield (title, start, end) for every ``Title\n-----`` section."""
    heads = [
        i
        for i in range(len(lines) - 1)
        if lines[i].strip() and UNDERLINE.match(lines[i + 1])
    ]
    for n, i in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        yield lines[i].strip(), i + 2, end


def section_for(version, text):
    lines = text.splitlines()
    for title, start, end in find_sections(lines):
        if title == version or title.startswith(version + " "):
            return "\n".join(lines[start:end]).strip()
    return None


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    version = argv[1].removeprefix("v")
    path = argv[2] if len(argv) == 3 else "HISTORY.rst"
    with open(path, encoding="utf-8") as fp:
        notes = section_for(version, fp.read())
    if not notes:
        print(f"No non-empty section for {version} in {path}", file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
