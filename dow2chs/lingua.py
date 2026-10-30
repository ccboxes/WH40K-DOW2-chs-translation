"""LinguaGacha 导入/导出。

使用 LinguaGacha 原生的 ``KV-JSON`` 格式：``{"英文原文": "中文译文"}``。
按英文原文去重后导出，相同原文共用一个译文，避免同一句话被翻译出多个版本；
需要按 key 单独处理时，直接改 ``data/catalog/translations.ndjson``。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import accepted_same_source, save_catalog
from .corpus import Corpus
from .games import GAME_ORDER
from .io_utils import write_text_exact
from .paths import CATALOG_PATH, GLOSSARY_PATH, LINGUA_INPUT_DIR
from .text import restore_edge_whitespace, validate_translation


class LinguaError(ValueError):
    pass


@dataclass
class ExportReport:
    target: str
    output: Path
    total_texts: int
    exported_texts: int
    prefilled_texts: int
    skipped_complete: int
    conflicting_texts: int
    key_count: int


@dataclass
class ImportReport:
    updated_keys: int = 0
    updated_texts: int = 0
    kept_existing: int = 0
    skipped_same: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    invalid: list[tuple[str, list[str]]] = field(default_factory=list)
    warnings: list[tuple[str, list[str]]] = field(default_factory=list)
    accepted_same: int = 0

    @property
    def has_problems(self) -> bool:
        return bool(self.invalid or self.unknown)


def _read_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise LinguaError(f"{path} 不是 UTF-8：{error.reason}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise LinguaError(f"{path} 不是合法 JSON：{error.msg}") from error


def _write_json(path: Path, data: object) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=4) + "\n"
    write_text_exact(path, text)


def read_glossary(path: Path = GLOSSARY_PATH) -> list[dict[str, object]]:
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for number, line in enumerate(file, start=1):
            line = line.rstrip("\r\n")
            if line.strip() == "" or line.lstrip().startswith("#"):
                continue
            columns = line.split("\t")
            if columns[0].strip().lower() == "src":
                continue
            if len(columns) < 2:
                raise LinguaError(f"{path}:{number} 至少需要 src 和 dst 两列")
            source, target = columns[0], columns[1]
            info = columns[2] if len(columns) > 2 else ""
            if source == "" or target == "":
                raise LinguaError(f"{path}:{number} 的 src/dst 不能为空")
            entries.append(
                {
                    "src": source,
                    "dst": target,
                    "info": info,
                    "regex": False,
                    "case_sensitive": False,
                }
            )
    return entries


def export_lingua(
    corpus: Corpus,
    translations: dict[str, str],
    out_dir: Path = LINGUA_INPUT_DIR,
    *,
    game: str | None = None,
    include_all: bool = False,
) -> ExportReport:
    if game is None:
        target_games = tuple(key for key in GAME_ORDER if key in corpus.games)
        target_name = "all"
    else:
        if game not in corpus.games:
            raise LinguaError(f"没有加载游戏：{game}")
        target_games = (game,)
        target_name = game

    target_keys = corpus.keys_for(target_games)
    seen: set[str] = set()
    ordered_texts: list[str] = []
    for game_key in target_games:
        for entry in corpus.games[game_key]:
            if entry.text not in seen:
                seen.add(entry.text)
                ordered_texts.append(entry.text)

    data: dict[str, str] = {}
    skipped_complete = 0
    prefilled = 0
    conflicts = 0

    for text in ordered_texts:
        keys = [key for key in corpus.text_to_keys.get(text, []) if key in target_keys]
        if not keys:
            continue
        values = [translations[key] for key in keys if key in translations]
        unique_values = set(values)
        complete = len(values) == len(keys) and len(unique_values) == 1

        if complete and not include_all:
            skipped_complete += 1
            continue
        if len(unique_values) > 1:
            conflicts += 1

        prefill = next(iter(unique_values)) if complete else ""
        if prefill:
            prefilled += 1
        data[text] = prefill

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = "dow2-retribution.json" if game is None else f"{game}.json"
    output = out_dir / filename
    _write_json(output, data)

    glossary = read_glossary()
    glossary_path = out_dir / "glossary.json"
    if glossary:
        _write_json(glossary_path, glossary)
    elif glossary_path.exists():
        glossary_path.unlink()

    manifest = {
        "schema": 1,
        "kind": "linguagacha-kv-json",
        "target": target_name,
        "source_sha256": {
            key: corpus.source_hashes[key] for key in target_games
        },
        "target_keys": len(target_keys),
        "unique_texts": len(ordered_texts),
        "exported_texts": len(data),
        "skipped_complete": skipped_complete,
        "include_all": include_all,
    }
    _write_json(out_dir / "manifest.json", manifest)

    instructions = (
        "LinguaGacha 导入说明\n"
        "====================\n\n"
        "1. 在 LinguaGacha 中把 dow2-retribution.json 拖入项目。\n"
        "2. 原文语言：English；译文语言：中文（简体）。\n"
        "3. 文件是 KV-JSON：对象 key 是英文原文，value 是已有译文。\n"
        "   不要手工翻译 key，也不要把 key 改成数字 ID。\n"
        "4. 如果生成了 glossary.json，在术语表页面导入它。\n"
        "5. 翻译完成后用“生成译文”，把输出 JSON 交给：\n"
        "   python -m dow2chs import <输出 JSON>\n\n"
        "导出是按英文原文去重的：相同原文共用一个译文。\n"
        "若某个 key 需要不同译法，翻译后直接编辑\n"
        "data/catalog/translations.ndjson 对应行。\n"
    )
    write_text_exact(out_dir / "README.txt", instructions)

    return ExportReport(
        target=target_name,
        output=output,
        total_texts=len(ordered_texts),
        exported_texts=len(data),
        prefilled_texts=prefilled,
        skipped_complete=skipped_complete,
        conflicting_texts=conflicts,
        key_count=len(target_keys),
    )


def find_output_file(path: Path) -> Path:
    if path.is_file():
        return path
    if not path.exists():
        raise LinguaError(f"路径不存在：{path}")
    candidates = []
    for item in sorted(path.rglob("*.json")):
        if item.name in {"manifest.json", "glossary.json"}:
            continue
        if "input" in item.relative_to(path).parts:
            continue
        candidates.append(item)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise LinguaError(f"{path} 下没有找到译文 JSON")
    listing = "\n".join(f"  {item}" for item in candidates[:20])
    raise LinguaError(f"{path} 下有多个候选文件，请指定其中一个：\n{listing}")


def import_lingua(
    path: Path,
    corpus: Corpus,
    translations: dict[str, str],
    *,
    accept_same: bool = False,
    keep_existing: bool = False,
    dry_run: bool = False,
    catalog_path: Path = CATALOG_PATH,
) -> ImportReport:
    output_file = find_output_file(path)
    data = _read_json(output_file)
    if not isinstance(data, dict):
        raise LinguaError(
            f"{output_file} 不是 KV-JSON 对象。"
            "本工具导出的是 {英文: 译文}；Message-JSON 数组不能直接导入。"
        )

    report = ImportReport()
    for source, value in data.items():
        if not isinstance(source, str) or not isinstance(value, str):
            report.invalid.append((str(source)[:80], ["key 或 value 不是字符串"]))
            continue

        keys = corpus.text_to_keys.get(source)
        if not keys:
            report.unknown.append(source[:120])
            continue

        if value == "":
            report.empty.append(source[:120])
            continue
        if value.strip() == "" and source.strip() != "":
            report.empty.append(source[:120])
            continue

        fixed = restore_edge_whitespace(source, value)
        if fixed == source:
            if accept_same or accepted_same_source(source):
                report.accepted_same += 1
            else:
                report.skipped_same.append(source[:120])
                continue

        errors, warnings = validate_translation(source, fixed)
        if warnings:
            report.warnings.append((source[:80], warnings))
        if errors:
            report.invalid.append((source[:80], errors))
            continue

        changed_keys = 0
        for key in keys:
            if keep_existing and key in translations:
                report.kept_existing += 1
                continue
            translations[key] = fixed
            changed_keys += 1
        if changed_keys:
            report.updated_keys += changed_keys
            report.updated_texts += 1

    if not dry_run and (report.updated_keys or catalog_path.exists()):
        save_catalog(translations, catalog_path)

    return report
