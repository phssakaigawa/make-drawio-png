"""CLI entry point — invoked as ``make-drawio-png`` or ``python -m make_drawio_png``."""

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Shoichiro Sakaigawa

from __future__ import annotations

import sys

from make_drawio_png import drawio_to_png, __version__

_USAGE = """\
make-drawio-png  v{version}
Convert a .drawio XML file into a re-editable .drawio.png (zero dependencies).

Usage:
  make-drawio-png <input.drawio> [output.drawio.png]

Arguments:
  input.drawio        Source draw.io XML file.
  output.drawio.png   Output path (default: <input.drawio>.png).

Examples:
  make-drawio-png architecture.drawio
  make-drawio-png flow.drawio  docs/images/flow.drawio.png
""".format(version=__version__)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(_USAGE)
        sys.exit(0 if args and args[0] in ("-h", "--help") else 1)

    src = args[0]
    dst = args[1] if len(args) >= 2 else None
    drawio_to_png(src, dst)


if __name__ == "__main__":
    main()
