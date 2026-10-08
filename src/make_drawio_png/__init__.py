"""
make_drawio_png
===============
Convert a .drawio XML file into a re-editable .drawio.png — zero external
dependencies, pure Python standard library.

The .drawio.png format embeds the diagram XML inside a PNG ``tEXt`` chunk
(keyword ``mxfile``, value URL-encoded UTF-8 XML).  draw.io / diagrams.net
reads that chunk to restore the diagram, so the file is both a valid PNG
*and* a fully editable draw.io source.

Quick start
-----------
    # CLI
    make-drawio-png architecture.drawio
    make-drawio-png flow.drawio flow.drawio.png
    python -m make_drawio_png architecture.drawio

    # Python API
    from make_drawio_png import drawio_to_png
    drawio_to_png("architecture.drawio")
    drawio_to_png("flow.drawio", "docs/images/flow.drawio.png")
"""

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Shoichiro Sakaigawa

from __future__ import annotations

import struct
import zlib
from urllib.parse import quote

__version__ = "0.1.0"
__all__ = ["drawio_to_png"]


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
    image size, so a 1×1 placeholder is sufficient.  The PNG acts only as a
    container for the embedded tEXt chunk.
    """
    PNG_SIG = b"\x89PNG\r\n\x1a\n"

    # IHDR: width=1, height=1, bit_depth=8, color_type=2 (RGB),
    #        compression=0, filter=0, interlace=0
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = _png_chunk(b"IHDR", ihdr_data)

    # IDAT: single white RGB pixel with PNG filter byte 0
    idat = _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))

    iend = _png_chunk(b"IEND", b"")
    return PNG_SIG + ihdr + idat + iend


def _embed_text_chunk(png_bytes: bytes, keyword: str, text: str) -> bytes:
    """
    Insert a ``tEXt`` chunk immediately before the first ``IDAT`` chunk.

    draw.io expects:
      - chunk type  : ``tEXt``
      - keyword     : ``"mxfile"``  (ASCII)
      - text value  : URL-encoded (UTF-8) mxfile XML — results in ASCII only

    *text* must already be URL-encoded (ASCII only) before being passed here.
    """
    sig = png_bytes[:8]
    body = png_bytes[8:]

    # tEXt layout:  keyword NUL text  (all ASCII)
    chunk_data = keyword.encode("ascii") + b"\x00" + text.encode("ascii")
    text_chunk = _png_chunk(b"tEXt", chunk_data)

    # Locate the IDAT chunk-type field; insert before its 4-byte length field
    idat_type_offset = body.find(b"IDAT")
    insert_at = max(idat_type_offset - 4, 0)

    return sig + body[:insert_at] + text_chunk + body[insert_at:]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def drawio_to_png(drawio_path: str, output_path: str | None = None) -> str:
    """
    Read a ``.drawio`` XML file and write a re-editable ``.drawio.png``.

    Parameters
    ----------
    drawio_path:
        Path to the source ``.drawio`` file.
    output_path:
        Destination path.  Defaults to ``drawio_path + ".png"``.

    Returns
    -------
    str
        Path of the written PNG file.
    """
    if output_path is None:
        output_path = drawio_path + ".png"

    with open(drawio_path, encoding="utf-8") as fh:
        xml_text = fh.read()

    # URL-encode the XML: UTF-8 percent-encoding → ASCII-only result
    encoded = quote(xml_text, safe="", encoding="utf-8")

    png = _make_minimal_png()
    png = _embed_text_chunk(png, "mxfile", encoded)

    with open(output_path, "wb") as fh:
        fh.write(png)

    size_kb = len(png) / 1024
    print(f"[make_drawio_png] {output_path}  ({size_kb:.1f} KB)")
    return output_path
