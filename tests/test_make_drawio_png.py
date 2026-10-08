"""Tests for make_drawio_png."""

import os
import struct
import zlib
from pathlib import Path
from urllib.parse import unquote

import pytest

from make_drawio_png import (
    DrawioCLINotFoundError,
    __version__,
    drawio_export,
    drawio_render_png,
    drawio_to_png,
    find_drawio_cli,
)


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


def _get_mxfile_xml(png_path: str) -> str:
    """Extract and decode the mxfile XML embedded in a .drawio.png."""
    data = Path(png_path).read_bytes()
    chunks = _read_png_chunks(data)
    text_chunks = [(t, d) for t, d in chunks if t == "tEXt"]
    assert text_chunks, "No tEXt chunk found"
    keyword, _, value = text_chunks[0][1].partition(b"\x00")
    assert keyword == b"mxfile"
    return unquote(value.decode("ascii"), encoding="utf-8")


def _has_drawio_cli() -> bool:
    try:
        find_drawio_cli()
        return True
    except DrawioCLINotFoundError:
        return False


requires_drawio = pytest.mark.skipif(
    not _has_drawio_cli(),
    reason="draw.io CLI not installed (winget install JGraph.Draw / brew install --cask drawio)",
)


# ---------------------------------------------------------------------------
# Tests: version
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_string(self):
        assert isinstance(__version__, str)
        assert __version__.count(".") >= 1


# ---------------------------------------------------------------------------
# Tests: find_drawio_cli
# ---------------------------------------------------------------------------

class TestFindDrawioCli:
    def test_env_var_override(self, tmp_path: Path):
        fake_exe = tmp_path / "drawio.exe"
        fake_exe.write_bytes(b"")
        os.environ["DRAWIO_PATH"] = str(fake_exe)
        try:
            result = find_drawio_cli()
            assert result == str(fake_exe)
        finally:
            del os.environ["DRAWIO_PATH"]

    def test_not_found_raises(self, monkeypatch):
        monkeypatch.delenv("DRAWIO_PATH", raising=False)
        monkeypatch.setattr("shutil.which", lambda _: None)
        # Patch candidates to empty so it always raises
        import make_drawio_png as m
        orig = m._DRAWIO_CANDIDATES
        m._DRAWIO_CANDIDATES = {}
        try:
            with pytest.raises(DrawioCLINotFoundError):
                find_drawio_cli()
        finally:
            m._DRAWIO_CANDIDATES = orig

    @requires_drawio
    def test_finds_installed_drawio(self):
        path = find_drawio_cli()
        assert Path(path).is_file()


# ---------------------------------------------------------------------------
# Tests: drawio_to_png (embed only)
# ---------------------------------------------------------------------------

class TestDrawioToPng:
    def test_creates_output_file(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        assert Path(result).exists()

    def test_default_output_path(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        assert Path(result) == drawio_file.parent / (drawio_file.name + ".png")

    def test_explicit_output_path(self, drawio_file: Path, tmp_path: Path):
        out = tmp_path / "custom.drawio.png"
        result = drawio_to_png(str(drawio_file), str(out))
        assert Path(result) == out
        assert out.exists()

    def test_output_is_valid_png(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        assert Path(result).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_contains_mxfile_text_chunk(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        xml = _get_mxfile_xml(result)
        assert xml.startswith("<mxfile")

    def test_embedded_xml_roundtrips(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        assert _get_mxfile_xml(result) == MINIMAL_DRAWIO

    def test_japanese_survives_roundtrip(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        assert "日本語" in _get_mxfile_xml(result)

    def test_text_chunk_before_idat(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        chunks = _read_png_chunks(Path(result).read_bytes())
        types = [t for t, _ in chunks]
        assert types.index("tEXt") < types.index("IDAT")

    def test_all_chunk_crcs_valid(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        data = Path(result).read_bytes()
        i = 8
        while i < len(data):
            length = struct.unpack(">I", data[i : i + 4])[0]
            chunk_type = data[i + 4 : i + 8]
            chunk_data = data[i + 8 : i + 8 + length]
            stored = struct.unpack(">I", data[i + 8 + length : i + 12 + length])[0]
            expected = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
            assert stored == expected, f"CRC mismatch in chunk {chunk_type}"
            i += 12 + length

    def test_ends_with_iend(self, drawio_file: Path):
        result = drawio_to_png(str(drawio_file))
        chunks = _read_png_chunks(Path(result).read_bytes())
        assert chunks[-1][0] == "IEND"


# ---------------------------------------------------------------------------
# Tests: drawio_render_png (render only, requires draw.io CLI)
# ---------------------------------------------------------------------------

@requires_drawio
class TestDrawioRenderPng:
    def test_creates_rendered_png(self, drawio_file: Path):
        out = str(drawio_file.with_suffix(".png"))
        result = drawio_render_png(str(drawio_file), out)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 1000  # real image, not placeholder

    def test_output_is_valid_png(self, drawio_file: Path):
        out = str(drawio_file.with_suffix(".png"))
        result = drawio_render_png(str(drawio_file), out)
        assert Path(result).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_no_mxfile_chunk(self, drawio_file: Path):
        """drawio_render_png does NOT embed XML — that's drawio_export's job."""
        out = str(drawio_file.with_suffix(".png"))
        result = drawio_render_png(str(drawio_file), out)
        chunks = _read_png_chunks(Path(result).read_bytes())
        text_keywords = []
        for t, d in chunks:
            if t == "tEXt":
                kw, _, _ = d.partition(b"\x00")
                text_keywords.append(kw.decode("ascii", errors="replace"))
        assert "mxfile" not in text_keywords


# ---------------------------------------------------------------------------
# Tests: drawio_export (render + embed, requires draw.io CLI)
# ---------------------------------------------------------------------------

@requires_drawio
class TestDrawioExport:
    def test_creates_drawio_png(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        assert Path(result).exists()

    def test_default_output_path(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        assert Path(result) == drawio_file.parent / (drawio_file.name + ".png")

    def test_output_is_valid_png(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        assert Path(result).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_has_mxfile_text_chunk(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        xml = _get_mxfile_xml(result)
        assert xml.startswith("<mxfile")

    def test_japanese_survives_roundtrip(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        assert "日本語" in _get_mxfile_xml(result)

    def test_rendered_image_is_not_placeholder(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        assert Path(result).stat().st_size > 1000  # real rendered content

    def test_text_chunk_before_idat(self, drawio_file: Path):
        result = drawio_export(str(drawio_file))
        chunks = _read_png_chunks(Path(result).read_bytes())
        types = [t for t, _ in chunks]
        assert types.index("tEXt") < types.index("IDAT")
