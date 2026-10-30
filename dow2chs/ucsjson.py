"""把 UCS 解包成 JSON、再从 JSON 打包回 UCS。"""

from __future__ import annotations

import json
from pathlib import Path

from .io_utils import write_text_exact
from .ucs import Entry, UcsDocument, UcsError, load, save

SCHEMA = "dow2-ucs/1"
ENCODING = "utf-16-le"


def document_to_payload(document: UcsDocument) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "encoding": ENCODING,
        "bom": document.has_bom,
        "final_newline": document.final_newline,
        "entries": [{"key": entry.key, "text": entry.text} for entry in document.entries],
    }


def payload_to_document(payload: object) -> UcsDocument:
    if not isinstance(payload, dict):
        raise UcsError("解包 JSON 顶层必须是对象")
    if payload.get("schema") != SCHEMA:
        raise UcsError(f"schema 必须是 {SCHEMA}")
    if payload.get("encoding") != ENCODING:
        raise UcsError(f"encoding 必须是 {ENCODING}")

    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise UcsError("entries 必须是数组")

    entries: list[Entry] = []
    seen: set[str] = set()
    for number, record in enumerate(raw_entries, start=1):
        if not isinstance(record, dict):
            raise UcsError(f"entries[{number}] 必须是对象")
        key = record.get("key")
        text = record.get("text")
        if not isinstance(key, str) or not key.isdigit():
            raise UcsError(f"entries[{number}].key 必须是数字字符串")
        if not isinstance(text, str):
            raise UcsError(f"entries[{number}].text 必须是字符串")
        if "\r" in text:
            raise UcsError(f"entries[{number}].text 含 CR")
        if key in seen:
            raise UcsError(f"key 重复：{key}")
        seen.add(key)
        entries.append(Entry(key=key, text=text))

    return UcsDocument(
        entries=entries,
        has_bom=bool(payload.get("bom", True)),
        final_newline=bool(payload.get("final_newline", True)),
    )


def unpack_file(source: Path, destination: Path) -> int:
    document = load(source, strict_source=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        document_to_payload(document), ensure_ascii=False, indent=2
    ) + "\n"
    write_text_exact(destination, text)
    return len(document.entries)


def pack_file(source: Path, destination: Path) -> int:
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise UcsError(f"{source} 不是合法 JSON：{error.msg}") from error
    document = payload_to_document(payload)
    save(destination, document)

    # 回读，确保写出的是合法 UCS。
    reloaded = load(destination, strict_source=False)
    if reloaded.entries != document.entries:
        raise UcsError(f"{destination} 回读校验失败")
    return len(document.entries)
