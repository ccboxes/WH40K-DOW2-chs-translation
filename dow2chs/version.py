"""版本号与 CHANGELOG 维护。"""

from __future__ import annotations

import datetime as _date
import re
from pathlib import Path

from .io_utils import write_text_exact
from .paths import CHANGELOG_PATH, VERSION_PATH

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
UNRELEASED_RE = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)


class VersionError(ValueError):
    pass


def read_version(path: Path = VERSION_PATH) -> str:
    if not path.exists():
        raise VersionError(f"缺少版本文件：{path}")
    version = path.read_text(encoding="utf-8").strip()
    if not SEMVER_RE.fullmatch(version):
        raise VersionError(f"VERSION 不是合法 SemVer：{version!r}")
    return version


def write_version(version: str, path: Path = VERSION_PATH) -> None:
    if not SEMVER_RE.fullmatch(version):
        raise VersionError(f"不是合法 SemVer：{version!r}")
    write_text_exact(path, version + "\n")


def changelog_has_version(version: str, path: Path = CHANGELOG_PATH) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"^## \[" + re.escape(version) + r"\]", re.MULTILINE)
    return pattern.search(text) is not None


def set_version(version: str, path: Path = VERSION_PATH, changelog: Path = CHANGELOG_PATH) -> None:
    """更新 VERSION，并把 Unreleased 下已有内容移到新版本标题下。"""
    if not SEMVER_RE.fullmatch(version):
        raise VersionError(f"不是合法 SemVer：{version!r}")
    write_version(version, path)

    if not changelog.exists():
        raise VersionError(f"缺少 CHANGELOG：{changelog}")
    text = changelog.read_text(encoding="utf-8")
    heading = f"## [{version}]"
    if heading in text:
        return

    match = UNRELEASED_RE.search(text)
    if match is None:
        raise VersionError("CHANGELOG.md 缺少 '## [Unreleased]' 标题")

    section_start = match.end()
    next_heading = re.search(r"^## ", text[section_start:], re.MULTILINE)
    section_end = section_start + next_heading.start() if next_heading else len(text)
    body = text[section_start:section_end].strip("\n")
    before = text[:section_start].rstrip("\n")
    after = text[section_end:]

    date = _date.date.today().isoformat()
    new_section = f"## [{version}] - {date}"
    if body:
        new_section += "\n\n" + body
    new_section += "\n\n"

    updated = before + "\n\n" + new_section + after
    write_text_exact(changelog, updated)
