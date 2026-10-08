# Embedding Beautiful Diagrams in Documents with Bob + draw.io CLI

This guide explains how to use an AI agent (Bob / Claude Code) to automatically generate
`.drawio` XML, then produce a **visually rendered, re-editable PNG** using `make-drawio-png`
and the draw.io CLI — ready to embed in any Markdown document or README.

---

## Why Not Text-Based Diagrams?

| Approach | Visual quality | Re-editable | AI-generatable |
|---|---|---|---|
| Mermaid / PlantUML | △ Simple | △ Text edit | ✅ |
| ASCII art | ✗ Coarse | ✗ | ✅ |
| `.drawio.png` (this guide) | ✅ High quality | ✅ draw.io app | ✅ |

A `.drawio.png` renders as a normal PNG image while also embedding the full diagram XML,
so draw.io can open and restore it for editing at any time.

---

## One-Time Setup

### 1. Install make-drawio-png

```bash
pip install make-drawio-png
```

> **Windows note:** If the `make-drawio-png` command is not found after installation,
> the Python Scripts directory is likely not on your PATH.
> Use `python -m make_drawio_png` instead — it works without any PATH changes.

### 2. Install draw.io desktop

```bash
# Windows
winget install JGraph.Draw

# macOS
brew install --cask drawio

# Linux
snap install drawio
```

The executable is auto-detected after installation.
To specify a custom path, set the environment variable:

```bash
# Windows
$env:DRAWIO_PATH = "C:\Users\you\AppData\Local\Programs\draw.io\draw.io.exe"

# macOS / Linux
export DRAWIO_PATH="/Applications/draw.io.app/Contents/MacOS/draw.io"
```

---

## Workflow Overview

![How make-drawio-png works](docs/how-it-works.drawio.png)

```
① Bob generates .drawio XML
       ↓
② make-drawio-png --render produces .drawio.png
   (draw.io CLI renders visually → XML embedded in tEXt chunk)
       ↓
③ Embed in Markdown / README
   ![Description](docs/architecture.drawio.png)
       ↓
④ Re-open in draw.io app for editing anytime
```

---

## How to Prompt Bob

### Basic prompt

```
Create a system architecture diagram using draw.io.
- Save the source as docs/architecture.drawio
- Run make-drawio-png --render to produce docs/architecture.drawio.png
- Embed the image in the "Architecture" section of README.md
```

### What Bob does internally

1. Generates and saves the `.drawio` XML
2. Renders + embeds via draw.io CLI:
   ```bash
   python3 -m make_drawio_png --render docs/architecture.drawio
   ```
3. Reads back the PNG with `read_file` for visual verification
4. Inserts `![](docs/architecture.drawio.png)` into the Markdown

---

## Usage Reference

| Scenario | Command / function | draw.io needed |
|---|---|---|
| Bob generates and immediately previews | `python -m make_drawio_png --render file.drawio` | ✅ |
| No draw.io / CI environment | `python -m make_drawio_png file.drawio` | ❌ |
| Python API — recommended | `drawio_export("file.drawio")` | ✅ |
| Python API — zero dependencies | `drawio_to_png("file.drawio")` | ❌ |

```python
from make_drawio_png import drawio_export, drawio_to_png

# Recommended: render + embed (visually rich output)
drawio_export("docs/architecture.drawio")
# → docs/architecture.drawio.png  (rendered + re-editable)

# Zero dependencies: embed only (placeholder image, re-editable)
drawio_to_png("docs/architecture.drawio")
# → docs/architecture.drawio.png  (1×1 placeholder, re-editable)
```

---

## draw.io XML Cheat Sheet (for Bob)

Minimal templates Bob can use when generating `.drawio` files.

### Basic structure

```xml
<mxfile host="app.diagrams.net">
  <diagram id="diagram-id" name="Page name">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- Add nodes and edges here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Common node styles

```xml
<!-- Rounded box -->
<mxCell id="2" value="Label"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
  vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="60" as="geometry"/>
</mxCell>

<!-- Swimlane -->
<mxCell id="3" value="Lane name"
  style="swimlane;startSize=30;fillColor=#f5f5f5;strokeColor=#666666;"
  vertex="1" parent="1">
  <mxGeometry x="40" y="40" width="400" height="300" as="geometry"/>
</mxCell>

<!-- Arrow / edge -->
<mxCell id="4" style="edgeStyle=orthogonalEdgeStyle;"
  edge="1" source="2" target="3" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

---

## Troubleshooting

### draw.io CLI not found

```
DrawioCLINotFoundError: draw.io CLI not found.
Install it with: winget install JGraph.Draw
```

→ Install draw.io desktop, or point to it via the `DRAWIO_PATH` environment variable.

### `make-drawio-png` command not found in Bob shell

Bob / Claude Code inherits the PATH from the process that launched it.
If the Python Scripts directory is missing from PATH, use `python -m`:

```bash
# May fail (Scripts not on PATH)
make-drawio-png --render file.drawio

# Always works
python3 -m make_drawio_png --render file.drawio
```

### PNG appears black or blank

You forgot the `--render` flag:

```bash
# Produces a 1×1 placeholder (no visual content)
python -m make_drawio_png file.drawio

# Produces a fully rendered image
python -m make_drawio_png --render file.drawio
```

### CJK characters appear garbled on Linux

This is a draw.io font issue. Install CJK fonts:

```bash
# Ubuntu / Debian
sudo apt-get install fonts-noto-cjk
```

---

## Related Links

- [make-drawio-png on GitHub](https://github.com/phssakaigawa/make-drawio-png)
- [draw.io desktop releases](https://github.com/jgraph/drawio-desktop/releases)
- [draw.io XML reference](https://jgraph.github.io/mxgraph/docs/js-api/files/model/mxCell-js.html)
