"""
make_drawio_png
===============
Convert a .drawio XML file into a re-editable .drawio.png — zero external
dependencies, pure Python standard library.

The .drawio.png format embeds the diagram XML inside a PNG ``tEXt`` chunk
(keyword ``mxfile``, value URL-encoded UTF-8 XML).  draw.io / diagrams.net
reads that chunk to restore the diagram, so the file is both a valid PNG
*and* a fully editable draw.io source.

Two rendering modes
-------------------
1. **Embed only** (zero dependencies) — ``drawio_to_png()``
   Produces a ``.drawio.png`` that is re-editable in draw.io but shows only a
   1×1 white pixel as a visual image.  No external tool required.

2. **Full render** (requires draw.io desktop) — ``drawio_render_png()``
   Uses the draw.io CLI to export a fully-rendered PNG image.

3. **Both at once** (recommended) — ``drawio_export()``
   Calls the draw.io CLI to render, then embeds the XML into that PNG so the
   result is *both* visually rich *and* re-editable.

Quick start
-----------
    # CLI
    make-drawio-png architecture.drawio            # embed only
    make-drawio-png --render architecture.drawio   # full render + embed
    python -m make_drawio_png --render flow.drawio

    # Python API
    from make_drawio_png import drawio_to_png, drawio_export
    drawio_to_png("architecture.drawio")           # embed only
    drawio_export("architecture.drawio")           # render + embed (recommended)

draw.io CLI installation
------------------------
draw.io desktop bundles a headless CLI exporter.  Install it once per machine:

  Windows : winget install JGraph.Draw
  macOS   : brew install --cask drawio
  Linux   : snap install drawio
            # or download .deb/.rpm from https://github.com/jgraph/drawio-desktop/releases

After installation the executable is auto-detected by this library.
You can also set the ``DRAWIO_PATH`` environment variable to point to a custom
location.
"""

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Shoichiro Sakaigawa

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from urllib.parse import quote

__version__ = "0.1.0"
__all__ = [
    "drawio_to_png",
    "drawio_render_png",
    "drawio_export",
    "find_drawio_cli",
    "DrawioCLINotFoundError",
]


# ---------------------------------------------------------------------------
# draw.io CLI detection
# ---------------------------------------------------------------------------

# Per-platform candidate paths (in priority order)
_DRAWIO_CANDIDATES: dict[str, list[str]] = {
    "win32": [
        r"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe",
        r"C:\Program Files\draw.io\draw.io.exe",
        r"C:\Program Files (x86)\draw.io\draw.io.exe",
    ],
    "darwin": [
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "/usr/local/bin/drawio",
    ],
    "linux": [
        "/snap/bin/drawio",
        "/usr/bin/drawio",
        "/usr/local/bin/drawio",
    ],
}


class DrawioCLINotFoundError(FileNotFoundError):
    """Raised when the draw.io CLI executable cannot be found.

    Install draw.io desktop:
      Windows : winget install JGraph.Draw
      macOS   : brew install --cask drawio
      Linux   : snap install drawio
    Or set the DRAWIO_PATH environment variable to the executable path.
    """


def find_drawio_cli() -> str:
    """
    Return the path to the draw.io CLI executable.

    Resolution order:
    1. ``DRAWIO_PATH`` environment variable
    2. ``drawio`` / ``draw.io`` on ``PATH`` (via shutil.which)
    3. Platform-specific default install locations

    Raises
    ------
    DrawioCLINotFoundError
        If the executable cannot be found.
    """
    # 1. Explicit env override
    env_path = os.environ.get("DRAWIO_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    # 2. PATH lookup
    for name in ("drawio", "draw.io"):
        found = shutil.which(name)
        if found:
            return found

    # 3. Platform default locations
    platform = sys.platform
    candidates = _DRAWIO_CANDIDATES.get(platform, [])
    for raw in candidates:
        expanded = Path(os.path.expandvars(raw))
        if expanded.is_file():
            return str(expanded)

    install_hint = {
        "win32":  "winget install JGraph.Draw",
        "darwin": "brew install --cask drawio",
        "linux":  "snap install drawio",
    }.get(platform, "https://github.com/jgraph/drawio-desktop/releases")

    raise DrawioCLINotFoundError(
        "draw.io CLI not found.\n"
        f"Install it with:  {install_hint}\n"
        "Or set the DRAWIO_PATH environment variable to the executable path."
    )


# ---------------------------------------------------------------------------
# Internal PNG helpers
# ---------------------------------------------------------------------------

def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk: [4-byte length][4-byte type][data][4-byte CRC]."""
    body = chunk_type + data
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + body + struct.pack(">I", crc)


def _make_minimal_png() -> bytes:
    """
    Return a 1×1 white RGB PNG.

    draw.io derives canvas dimensions from the embedded XML, not from the PNG
    image size, so a 1×1 placeholder is sufficient when rendering is not needed.
    """
    PNG_SIG = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = _png_chunk(b"IHDR", ihdr_data)
    idat = _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    iend = _png_chunk(b"IEND", b"")
    return PNG_SIG + ihdr + idat + iend


def _embed_text_chunk(png_bytes: bytes, keyword: str, text: str) -> bytes:
    """
    Insert a ``tEXt`` chunk immediately before the first ``IDAT`` chunk.

    draw.io expects:
      - chunk type  : ``tEXt``
      - keyword     : ``"mxfile"``
      - text value  : URL-encoded (UTF-8) mxfile XML  (ASCII only result)
    """
    sig = png_bytes[:8]
    body = png_bytes[8:]
    chunk_data = keyword.encode("ascii") + b"\x00" + text.encode("ascii")
    text_chunk = _png_chunk(b"tEXt", chunk_data)
    idat_type_offset = body.find(b"IDAT")
    insert_at = max(idat_type_offset - 4, 0)
    return sig + body[:insert_at] + text_chunk + body[insert_at:]


def _encode_xml(drawio_path: str) -> str:
    """Read a .drawio file and return its URL-encoded (UTF-8) content."""
    with open(drawio_path, encoding="utf-8") as fh:
        return quote(fh.read(), safe="", encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def drawio_to_png(drawio_path: str, output_path: str | None = None) -> str:
    """
    Embed a ``.drawio`` XML into a re-editable ``.drawio.png`` (no rendering).

    The output is a valid PNG containing only a 1×1 white placeholder image,
    but with the full diagram XML embedded in a ``tEXt[mxfile]`` chunk so
    draw.io can restore it.  No external tools required.

    For a visually rendered PNG use :func:`drawio_export` instead.

    Parameters
    ----------
    drawio_path:
        Path to the source ``.drawio`` file.
    output_path:
        Destination path.  Defaults to ``drawio_path + ".png"``.

    Returns
    -------
    str
        Path of the written ``.drawio.png`` file.
    """
    if output_path is None:
        output_path = drawio_path + ".png"

    encoded = _encode_xml(drawio_path)
    png = _make_minimal_png()
    png = _embed_text_chunk(png, "mxfile", encoded)

    with open(output_path, "wb") as fh:
        fh.write(png)

    print(f"[make_drawio_png] {output_path}  ({len(png) / 1024:.1f} KB)  [embed only]")
    return output_path


def drawio_render_png(
    drawio_path: str,
    output_path: str | None = None,
    *,
    scale: float = 1.0,
    quality: int = 100,
    drawio_cli: str | None = None,
) -> str:
    """
    Render a ``.drawio`` file to a PNG image using the draw.io CLI.

    The output is a fully-rendered PNG image (not re-editable by draw.io).
    For a re-editable rendered PNG use :func:`drawio_export` instead.

    Requires draw.io desktop to be installed.

    Parameters
    ----------
    drawio_path:
        Path to the source ``.drawio`` file.
    output_path:
        Destination path.  Defaults to ``drawio_path`` with ``.png`` extension.
    scale:
        Export scale factor (default 1.0).
    quality:
        PNG quality hint passed to draw.io (default 100).
    drawio_cli:
        Path to the draw.io executable.  Auto-detected when omitted.

    Returns
    -------
    str
        Path of the written PNG file.

    Raises
    ------
    DrawioCLINotFoundError
        If draw.io CLI cannot be found.
    subprocess.CalledProcessError
        If the draw.io CLI exits with a non-zero status.
    """
    src = Path(drawio_path)
    if output_path is None:
        output_path = str(src.with_suffix(".png"))

    cli = drawio_cli or find_drawio_cli()

    cmd = [
        cli,
        "--export",
        "--format", "png",
        "--scale", str(scale),
        "--quality", str(quality),
        "--output", output_path,
        str(src),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    size_kb = Path(output_path).stat().st_size / 1024
    print(f"[make_drawio_png] {output_path}  ({size_kb:.1f} KB)  [rendered]")
    return output_path


def drawio_export(
    drawio_path: str,
    output_path: str | None = None,
    *,
    scale: float = 1.0,
    quality: int = 100,
    drawio_cli: str | None = None,
) -> str:
    """
    Render a ``.drawio`` file and embed the XML — producing a fully-rendered,
    re-editable ``.drawio.png``.

    This is the **recommended** function: it combines :func:`drawio_render_png`
    (visual rendering via draw.io CLI) and :func:`drawio_to_png` (XML embedding)
    into a single step.

    Requires draw.io desktop to be installed.

    Parameters
    ----------
    drawio_path:
        Path to the source ``.drawio`` file.
    output_path:
        Destination path.  Defaults to ``drawio_path + ".png"``.
    scale:
        Export scale factor (default 1.0).
    quality:
        PNG quality hint (default 100).
    drawio_cli:
        Path to the draw.io executable.  Auto-detected when omitted.

    Returns
    -------
    str
        Path of the written ``.drawio.png`` file.

    Raises
    ------
    DrawioCLINotFoundError
        If draw.io CLI cannot be found.
    """
    if output_path is None:
        output_path = drawio_path + ".png"

    # Step 1: render to a temp file (draw.io replaces .drawio ext with .png)
    src = Path(drawio_path)
    rendered_path = str(src.with_suffix(".png"))

    cli = drawio_cli or find_drawio_cli()
    cmd = [
        cli,
        "--export",
        "--format", "png",
        "--scale", str(scale),
        "--quality", str(quality),
        "--output", rendered_path,
        str(src),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # Step 2: embed the XML tEXt chunk into the rendered PNG
    with open(rendered_path, "rb") as fh:
        png_bytes = fh.read()

    encoded = _encode_xml(drawio_path)
    png_bytes = _embed_text_chunk(png_bytes, "mxfile", encoded)

    with open(output_path, "wb") as fh:
        fh.write(png_bytes)

    # Clean up intermediate file if it differs from the final output
    if Path(rendered_path).resolve() != Path(output_path).resolve():
        Path(rendered_path).unlink(missing_ok=True)

    size_kb = len(png_bytes) / 1024
    print(f"[make_drawio_png] {output_path}  ({size_kb:.1f} KB)  [rendered + embedded]")
    return output_path
