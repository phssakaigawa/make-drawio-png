"""CLI entry point — invoked as ``make-drawio-png`` or ``python -m make_drawio_png``."""

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Shoichiro Sakaigawa

from __future__ import annotations

import argparse
import sys

from make_drawio_png import (
    DrawioCLINotFoundError,
    drawio_export,
    drawio_to_png,
    find_drawio_cli,
    __version__,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="make-drawio-png",
        description=(
            "Convert a .drawio XML file into a re-editable .drawio.png.\n\n"
            "Modes:\n"
            "  (default)  Embed only — XML embedded in tEXt chunk, 1x1 placeholder image.\n"
            "             Zero dependencies. draw.io can restore the diagram.\n\n"
            "  --render   Render + embed — draw.io CLI renders the diagram visually,\n"
            "             then the XML is embedded. Requires draw.io desktop.\n"
            "             Install: winget install JGraph.Draw  (Windows)\n"
            "                      brew install --cask drawio  (macOS)\n"
            "                      snap install drawio         (Linux)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Source .drawio file")
    parser.add_argument("output", nargs="?", help="Output .drawio.png (default: <input>.png)")
    parser.add_argument(
        "--render", "-r",
        action="store_true",
        help="Use draw.io CLI to render a visual PNG before embedding XML",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Render scale factor (default: 1.0, used with --render)",
    )
    parser.add_argument(
        "--drawio-path",
        metavar="PATH",
        help="Path to draw.io executable (overrides DRAWIO_PATH env var)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if args.render:
        try:
            cli = args.drawio_path or find_drawio_cli()
        except DrawioCLINotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        drawio_export(
            args.input,
            args.output,
            scale=args.scale,
            drawio_cli=cli,
        )
    else:
        drawio_to_png(args.input, args.output)


if __name__ == "__main__":
    main()
