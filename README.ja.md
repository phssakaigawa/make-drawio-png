# make-drawio-png

[![PyPI version](https://img.shields.io/pypi/v/make-drawio-png)](https://pypi.org/project/make-drawio-png/)
[![Python](https://img.shields.io/pypi/pyversions/make-drawio-png)](https://pypi.org/project/make-drawio-png/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/phssakaigawa/make-drawio-png/blob/main/LICENSE)
[![CI](https://github.com/phssakaigawa/make-drawio-png/actions/workflows/ci.yml/badge.svg)](https://github.com/phssakaigawa/make-drawio-png/actions/workflows/ci.yml)

**[English README → README.md](https://github.com/phssakaigawa/make-drawio-png/blob/main/README.md)**

[draw.io / diagrams.net](https://www.diagrams.net/) が使用する **`.drawio.png` ファイル形式**を
実装した Python ライブラリです。

このライブラリを使うと、**draw.io を起動せずにプログラムから `.drawio.png` を生成**できます。
生成されたファイルは draw.io 本体がエクスポートしたものと完全に互換性があります。

### `.drawio.png` 形式とは？

`.drawio.png` ファイルは同時に2つの性質を持ちます：
- **標準的な PNG 画像** — あらゆる画像ビューア・ブラウザ・AI エージェントで表示できる
- **draw.io で完全に再編集できるソース** — draw.io で開くと図が復元され、編集できる

これは PNG の `tEXt` チャンク（`keyword=mxfile`、`value=URL-encoded UTF-8 XML`）に図の XML を
埋め込む [draw.io オープンソース仕様](https://github.com/jgraph/drawio) に準拠することで実現しています。
draw.io はこのチャンクを読んで図を復元し、画像ビューアはピクセルデータのみを参照します。

### ユースケース

- **AI エージェント / Bob**: 図をコードとして生成し、Markdown に埋め込んで PNG としてプレビュー
- **CI/CD パイプライン**: GUI なしで `.drawio` XML からアーキテクチャ図を生成
- **ドキュメント自動化**: レンダリング済み画像と再編集可能なソースを同一ファイルで管理

---

## インストール

```bash
pip install make-drawio-png
```

> **Windows ユーザーへ：** インストール後に `make-drawio-png` コマンドが見つからない場合は、
> Python の Scripts ディレクトリが PATH に入っていない可能性があります。
> `python -m make_drawio_png` を使えば PATH 設定不要です。詳細は [PATH ガイド](#windows--python-path-ガイド)を参照。

---

## 使い方

### CLI

```bash
# 埋め込みのみ — draw.io 不要・再編集可能（画像は 1×1 プレースホルダ）
python -m make_drawio_png architecture.drawio

# レンダリング + 埋め込み — 視覚的にきれいかつ再編集可能（draw.io デスクトップが必要）
python -m make_drawio_png --render architecture.drawio

# 出力先を明示
python -m make_drawio_png --render flow.drawio docs/images/flow.drawio.png
```

> **Windows / Bob shell ユーザーへ：** `make-drawio-png` コマンドの代わりに
> `python -m make_drawio_png` を使ってください。PATH 設定不要で常に動作します。

### Python API

```python
from make_drawio_png import drawio_export, drawio_to_png

# 推奨: レンダリング + 埋め込み（draw.io デスクトップが必要）
drawio_export("architecture.drawio")
# → architecture.drawio.png  (レンダリング済み + 再編集可能)

# 依存ゼロ: 埋め込みのみ（再編集可能、画像は 1×1 プレースホルダ）
drawio_to_png("architecture.drawio")
# → architecture.drawio.png  (再編集可能、視覚的な内容なし)
```

### draw.io デスクトップ（`--render` / `drawio_export` に必要）

```bash
winget install JGraph.Draw   # Windows
brew install --cask drawio   # macOS
snap install drawio          # Linux
```

インストール後は自動検出されます。
場所を明示したい場合は `DRAWIO_PATH` 環境変数で指定できます。

---

## Windows — Python PATH ガイド

Windows では `pip install` 後、`make-drawio-png` CLI スクリプトは
**デフォルトで PATH に入っていない** `Scripts` ディレクトリに置かれます。

| インストール方法 | Scripts ディレクトリ | PATH に入る？ |
|---|---|---|
| `pip install make-drawio-png`（システム全体） | `%LOCALAPPDATA%\Python\pythoncore-X.Y-64\Scripts` | ❌ 通常は入らない |
| `pip install --user make-drawio-png` | `%APPDATA%\Python\PythonXYZ\Scripts` | ❌ 通常は入らない |
| `pip install make-drawio-png`（venv 有効時） | `<venv>\Scripts` | ✅ venv 有効中のみ |

### Scripts パスの確認

```powershell
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
# 例: C:\Users\you\AppData\Local\Python\pythoncore-3.14-64\Scripts
```

### PATH への追加（一度だけ）

```powershell
$scripts = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "$([System.Environment]::GetEnvironmentVariable('PATH','User'));$scripts",
    "User"
)
# → ターミナルを再起動してください
```

### 回避策: `python -m` を使う

PATH を変更したくない場合はモジュールとして直接呼び出せます：

```powershell
python -m make_drawio_png --render architecture.drawio
```

---

## Bob / Claude Code shell

IBM Bob や Claude Code on Windows では、shell は **Bob/Claude を起動したプロセスの PATH を引き継ぎます**。

| 状況 | `python3` の解決先 | `make-drawio-png` CLI 使用可能？ |
|---|---|---|
| Python Scripts が PATH に入ったターミナルから起動 | your Python | ✅ |
| Windows スタートメニュー / システムトレイから起動 | システム PATH（Scripts なし） | ❌ `python -m` を使う |
| venv 有効な状態で起動 | venv Python + Scripts | ✅ |

**Bob / Claude Code ユーザーへの推奨：**

常に `python -m` で呼び出してください。PATH の問題を完全に回避できます：

```bash
# Bob の execute_command ツールから
python3 -m make_drawio_png --render "<path>.drawio"
```

---

## How it works（仕組み）

![make-drawio-png の仕組み](https://raw.githubusercontent.com/phssakaigawa/make-drawio-png/main/docs/how-it-works.ja.drawio.png)

`.drawio.png` ファイルは、通常の PNG 画像でありながら draw.io で再編集できるソースでもあります。  
draw.io は埋め込まれた `tEXt[mxfile]` チャンクを読んで図を完全に復元します。  
画像ビューアや AI エージェントは PNG のピクセルデータのみを参照します。

### PNG チャンク構造

```
PNG シグネチャ  (8 bytes)
IHDR チャンク   (25 bytes)
tEXt チャンク   (keyword="mxfile" \x00 URL-encoded XML)   ← 図の XML がここに
IDAT チャンク   (圧縮ピクセルデータ)
IEND チャンク
```

---

## 要件

- Python ≥ 3.9
- 外部依存なし（`struct`、`zlib`、`urllib.parse` のみ使用）
- レンダリング機能（`--render`）には draw.io デスクトップが必要

---

## ライセンス

MIT © 2026 Shoichiro Sakaigawa
