"""Tests for make_drawio_png."""

import struct
import zlib
from pathlib import Path
from urllib.parse import unquote

import pytest

from make_drawio_png import drawio_to_png, __version__


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_DRAWIO = """\
<mxfile host="app.diagrams.net">
  <diagram id="test-diagram" name="Test">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Hello 日本語" style="rounded=1;" vertex="1" parent="1">
          <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


@pytest.fixture
def drawio_file(tmp_path: Path) -> Path:
    p = tmp_path / "test.drawio"
    p.write_text(MINIMAL_DRAWIO, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_png_chunks(data: bytes) -> list[tuple[str, bytes]]:
    """Parse PNG into list of (chunk_type, chunk_data) tuples."""
    chunks = []
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG signature"
    i = 8
    while i < len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        chunk_type = data[i + 4 : i + 8].decode("ascii")
        chunk_data = data[i + 8 : i + 8 + length]
        chunks.append((chunk_type, chunk_data))
        i += 12 + length
    return chunks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_string(self):
        assert isinstance(__version__, str)
        assert __version__.count(".") >= 1


class TestDrawioToPng:
    def test_creates_output_file(self, drawio_file: Path):
        out = drawio_file.with_suffix(".drawio.png")
        result = drawio_to_png(str(drawio_file))
        assert Path(result).exists()
        assert Path(result) == drawio_file.parent / (drawio_file.name + ".png")

    def test_explicit_output_path(self, drawio_file: Path, tmp_path: Path):
        out = tmp_path / "custom_output.drawio.png"
        result = drawio_to_png(str(drawio_file), str(out))
        assert Path(result) == out
        assert out.exists()

    def test_returns_output_path(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        assert isinstance(result, str)

    def test_output_is_valid_png(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_contains_text_chunk_with_mxfile_keyword(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        chunks = _read_png_chunks(data)
        text_chunks = [(t, d) for t, d in chunks if t == "tEXt"]
        assert text_chunks, "No tEXt chunk found"
        keyword, _, value = text_chunks[0][1].partition(b"\x00")
        assert keyword == b"mxfile"

    def test_embedded_xml_roundtrips_correctly(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        chunks = _read_png_chunks(data)
        text_chunks = [(t, d) for t, d in chunks if t == "tEXt"]
        keyword, _, value = text_chunks[0][1].partition(b"\x00")

        # value is URL-encoded ASCII; decode back to UTF-8 XML
        decoded_xml = unquote(value.decode("ascii"), encoding="utf-8")
        assert decoded_xml == MINIMAL_DRAWIO

    def test_japanese_characters_survive_roundtrip(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        chunks = _read_png_chunks(data)
        text_chunks = [(t, d) for t, d in chunks if t == "tEXt"]
        keyword, _, value = text_chunks[0][1].partition(b"\x00")
        decoded_xml = unquote(value.decode("ascii"), encoding="utf-8")
        assert "日本語" in decoded_xml

    def test_text_chunk_is_before_idat(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        chunks = _read_png_chunks(data)
        types = [t for t, _ in chunks]
        text_idx = types.index("tEXt")
        idat_idx = types.index("IDAT")
        assert text_idx < idat_idx, "tEXt chunk must appear before IDAT"

    def test_png_chunks_have_valid_crcs(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        i = 8
        while i < len(data):
            length = struct.unpack(">I", data[i : i + 4])[0]
            chunk_type = data[i + 4 : i + 8]
            chunk_data = data[i + 8 : i + 8 + length]
            stored_crc = struct.unpack(">I", data[i + 8 + length : i + 12 + length])[0]
            expected_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
            assert stored_crc == expected_crc, f"CRC mismatch in chunk {chunk_type}"
            i += 12 + length

    def test_png_ends_with_iend(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        chunks = _read_png_chunks(data)
        assert chunks[-1][0] == "IEND"
