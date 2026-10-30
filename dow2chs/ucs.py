"""DOW2.ucs 的严格读写。

格式：UTF-16LE + BOM + CRLF，每行 ``key<TAB>text``。
文本值内可以出现 TAB、孤立 LF 和尾随空格，因此只能按 CRLF 拆行，
不能用 ``splitlines()`` 之类的通用拆行，也不能用文本模式读写。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

ENCODING = "utf-16-le"
BOM = "\ufeff"
CRLF = "\r\n"
SEP = "\t"


class UcsError(ValueError):
    """UCS 结构或编码不合法。"""


@dataclass(frozen=True)
class Entry:
    key: str
    text: str


@dataclass
class UcsDocument:
    entries: list[Entry] = field(default_factory=list)
    has_bom: bool = True
    final_newline: bool = True

    def by_key(self) -> dict[str, str]:
        return {entry.key: entry.text for entry in self.entries}


def parse_bytes(data: bytes, *, strict_source: bool = False) -> UcsDocument:
    """解析 UCS 字节，保留 BOM 与末尾换行信息以便无损回写。"""
    try:
        text = data.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise UcsError(f"不是合法的 UTF-16LE：{error.reason}") from error

    has_bom = text.startswith(BOM)
    if has_bom:
        text = text[1:]

    final_newline = text.endswith(CRLF)
    body = text[:-2] if final_newline else text

    if strict_source:
        if not has_bom:
            raise UcsError("缺少 UTF-16LE BOM")
        if not final_newline:
            raise UcsError("最后一行没有 CRLF 结尾")
        if body == "":
            raise UcsError("文件没有文本行")

    lines = [] if body == "" else body.split(CRLF)
    entries: list[Entry] = []
    seen: set[str] = set()

    for number, line in enumerate(lines, start=1):
        if line == "":
            raise UcsError(f"第 {number} 行为空行")
        if "\r" in line:
            raise UcsError(f"第 {number} 行含孤立 CR")
        if SEP not in line:
            raise UcsError(f"第 {number} 行没有 TAB 分隔符")
        key, value = line.split(SEP, 1)
        if not key.isdigit():
            raise UcsError(f"第 {number} 行的 key 不是数字：{key!r}")
        if key in seen:
            raise UcsError(f"key 重复：{key}")
        seen.add(key)
        entries.append(Entry(key=key, text=value))

    return UcsDocument(entries=entries, has_bom=has_bom, final_newline=final_newline)


def serialize(document: UcsDocument) -> bytes:
    """写出 UCS 字节。绝不使用文本模式，避免 CRLF 被二次转换。"""
    lines = [f"{entry.key}{SEP}{entry.text}" for entry in document.entries]
    body = CRLF.join(lines)
    if lines and document.final_newline:
        body += CRLF
    if document.has_bom:
        body = BOM + body
    return body.encode(ENCODING)


def load(path: Path, *, strict_source: bool = False) -> UcsDocument:
    if not path.exists():
        raise UcsError(f"文件不存在：{path}")
    return parse_bytes(path.read_bytes(), strict_source=strict_source)


def save(path: Path, document: UcsDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialize(document))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def roundtrip_bytes(data: bytes) -> bytes:
    return serialize(parse_bytes(data))
