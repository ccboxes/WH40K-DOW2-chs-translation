"""项目内固定路径。所有路径都按本文件位置解析，因此可在任意目录运行。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
SOURCE_DIR = DATA_DIR / "source"
FONT_DIR = DATA_DIR / "font_mapping"
CATALOG_DIR = DATA_DIR / "catalog"
CATALOG_PATH = CATALOG_DIR / "translations.ndjson"
GLOSSARY_PATH = DATA_DIR / "glossary" / "glossary.tsv"

WORK_DIR = ROOT / "work"
LINGUA_DIR = WORK_DIR / "lingua"
LINGUA_INPUT_DIR = LINGUA_DIR / "input"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"

VERSION_PATH = ROOT / "VERSION"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
