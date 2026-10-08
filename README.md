# make-drawio-png

[![PyPI version](https://img.shields.io/pypi/v/make-drawio-png)](https://pypi.org/project/make-drawio-png/)
[![Python](https://img.shields.io/pypi/pyversions/make-drawio-png)](https://pypi.org/project/make-drawio-png/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/phssakaigawa/make-drawio-png/blob/main/LICENSE)
[![CI](https://github.com/phssakaigawa/make-drawio-png/actions/workflows/ci.yml/badge.svg)](https://github.com/phssakaigawa/make-drawio-png/actions/workflows/ci.yml)

**[日本語版 README はこちら → README.ja.md](https://github.com/phssakaigawa/make-drawio-png/blob/main/README.ja.md)**

A Python library that implements the **`.drawio.png` file format** — the
re-editable PNG format used by [draw.io / diagrams.net](https://www.diagrams.net/).

With this library you can **generate `.drawio.png` files programmatically**,
without opening draw.io at all.  The generated files are indistinguishable
from those exported by draw.io itself.

### What is the `.drawio.png` format?

A `.drawio.png` file is simultaneously:
- a **standard PNG image** — viewable in any image viewer, browser, or AI agent
- a **fully editable draw.io source** — open it in draw.io to restore and edit the diagram

This is achieved by embedding the diagram XML inside a PNG `tEXt` chunk
(`keyword=mxfile`, `value=URL-encoded UTF-8 XML`), following the
[draw.io open-source specification](https://github.com/jgraph/drawio).
draw.io reads that chunk to restore the diagram; image viewers see only the PNG pixel data.

### Use cases

- **AI agents / Bob**: generate diagrams as code, embed them in Markdown docs, preview as PNG
- **CI/CD pipelines**: produce architecture diagrams from `.drawio` XML without a GUI
- **Documentation automation**: keep diagrams as re-editable sources alongside rendered images

---

## Install

```bash
pip install make-drawio-png
```

> **Note for Windows users — read the PATH section below before installing.**

---

## Usage

### CLI

```bash
# embed only — re-editable but 1×1 placeholder image (no draw.io needed)
python -m make_drawio_png architecture.drawio

# render + embed — visually rendered AND re-editable (requires draw.io desktop)
python -m make_drawio_png --render architecture.drawio

# explicit output path
python -m make_drawio_png --render flow.drawio docs/images/flow.drawio.png
```

> **Windows / Bob shell users:** Use `python -m make_drawio_png` instead of the
> `make-drawio-png` command — it works without any PATH changes.  See the
> [PATH guide](#windows--python-path-guide) below.

### Python API

```python
from make_drawio_png import drawio_export, drawio_to_png

# Recommended: render + embed (requires draw.io desktop)
drawio_export("architecture.drawio")
# → architecture.drawio.png  (rendered + re-editable)

# Zero dependencies: embed only (re-editable, 1×1 placeholder image)
drawio_to_png("architecture.drawio")
# → architecture.drawio.png  (re-editable, no visual content)
```

### draw.io desktop (required for `--render` / `drawio_export`)

```bash
winget install JGraph.Draw   # Windows
brew install --cask drawio   # macOS
snap install drawio          # Linux
```

The CLI is auto-detected after installation.
Set `DRAWIO_PATH` to override the location.

---

## Windows — Python PATH guide

On Windows, `pip install` places the `make-drawio-png` CLI script in a
`Scripts` directory that is **not always in PATH by default**.  
The table below shows where scripts land depending on how you install:

| Install command | Scripts directory | In PATH by default? |
|---|---|---|
| `pip install make-drawio-png` (system-wide) | `%LOCALAPPDATA%\Python\pythoncore-X.Y-64\Scripts` | ❌ usually not |
| `pip install --user make-drawio-png` | `%APPDATA%\Python\PythonXYZ\Scripts` | ❌ usually not |
| `pip install make-drawio-png` (venv active) | `<venv>\Scripts` | ✅ while venv is active |

### Checking your Scripts path

```powershell
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
# e.g. C:\Users\you\AppData\Local\Python\pythoncore-3.14-64\Scripts

python -c "import sysconfig; print(sysconfig.get_path('scripts','nt_user'))"
# e.g. C:\Users\you\AppData\Roaming\Python\Python314\Scripts
```

### Adding Scripts to PATH (one-time setup)

```powershell
# Append to your user PATH permanently
$scripts = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "$([System.Environment]::GetEnvironmentVariable('PATH','User'));$scripts",
    "User"
)
# → restart your terminal / shell after this
```

### Workaround: use `python -m` instead of the CLI

If you don't want to touch PATH at all, call the module directly:

```powershell
python -m make_drawio_png architecture.drawio
```

This always works regardless of PATH because Python itself is on PATH.

---

## Bob / Claude Code shell

When using IBM Bob or Claude Code on Windows, the shell inherits the **same
PATH as the process that launched Bob/Claude** — there is no separate Python
environment.

| Scenario | `python3` resolves to | `make-drawio-png` CLI available? |
|---|---|---|
| Launched from a terminal where Python Scripts is in PATH | your Python installation | ✅ |
| Launched from Windows start menu / system tray | system PATH (Scripts likely missing) | ❌ use `python -m` |
| Launched inside an active venv | venv Python + Scripts | ✅ |

**Recommended practice for Bob/Claude Code users:**

Always invoke via `python -m` so the PATH question is irrelevant:

```python
# In Bob's execute_command tool
python3 -m make_drawio_png "<path>.drawio"
```

Or reference the script by its absolute path after installation:

```python
import subprocess, sysconfig, pathlib
scripts = pathlib.Path(sysconfig.get_path("scripts"))
subprocess.run([scripts / "make-drawio-png", "architecture.drawio"])
```

---

## How it works

![How make-drawio-png works](https://raw.githubusercontent.com/phssakaigawa/make-drawio-png/main/docs/how-it-works.drawio.png)

The `.drawio.png` file is both a valid PNG image and a re-editable draw.io
source.  draw.io reads the embedded `tEXt[mxfile]` chunk to restore the full
diagram; image viewers and AI agents see only the PNG pixel data.

### PNG chunk layout

```
PNG Signature  (8 bytes)
IHDR chunk     (25 bytes)
tEXt chunk     (keyword="mxfile" \x00 URL-encoded-XML)   ← diagram XML here
IDAT chunk     (compressed pixel data)
IEND chunk
```

---

## Requirements

- Python ≥ 3.9
- No external dependencies (uses only `struct`, `zlib`, `urllib.parse` from stdlib)

---

## License

MIT © 2026 Shoichiro Sakaigawa
