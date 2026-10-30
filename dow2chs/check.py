"""项目自检：原版、译本、格式符、字体映射。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import CatalogError, load_catalog
from .corpus import Corpus, SourceError, load_corpus
from .games import GAME_ORDER, GAMES, font_mapping, source_ucs
from .source import verify as verify_source
from .text import validate_translation
from .ucs import UcsError, load, roundtrip_bytes


@dataclass
class CheckReport:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    coverage: dict[str, tuple[int, int]] = field(default_factory=dict)
    corpus: Corpus | None = None
    translations: dict[str, str] = field(default_factory=dict)


def check_project(*, roundtrip: bool = True) -> CheckReport:
    report = CheckReport()

    source_problems = verify_source()
    report.problems.extend(source_problems)

    try:
        corpus = load_corpus()
    except SourceError as error:
        report.problems.append(str(error))
        return report

    report.corpus = corpus

    try:
        translations = load_catalog()
    except CatalogError as error:
        report.problems.append(str(error))
        return report

    report.translations = translations

    unknown = sorted(set(translations) - corpus.all_keys(), key=int)
    if unknown:
        report.problems.append(
            f"译本目录有 {len(unknown)} 个原版不存在的 key，例如："
            + "、".join(unknown[:20])
        )

    for game_key in GAME_ORDER:
        if game_key not in corpus.games:
            continue
        keys = [entry.key for entry in corpus.games[game_key]]
        translated = sum(1 for key in keys if key in translations)
        report.coverage[game_key] = (translated, len(keys))

    invalid = 0
    warned = 0
    for key, text in translations.items():
        source = corpus.key_to_text.get(key)
        if source is None:
            continue
        errors, warnings = validate_translation(source, text)
        if errors:
            invalid += 1
            if invalid <= 30:
                report.problems.append(f"key {key}：" + "；".join(errors))
        if warnings:
            warned += 1
            if warned <= 30:
                report.warnings.append(f"key {key}：" + "；".join(warnings))
    if invalid > 30:
        report.problems.append(f"共 {invalid} 条格式校验失败，仅列出前 30 条")
    if warned > 30:
        report.warnings.append(f"共 {warned} 条格式警告，仅列出前 30 条")

    for game in GAMES.values():
        if game.key not in corpus.games:
            continue
        path = font_mapping(game)
        if not path.exists():
            report.problems.append(f"缺少字体映射：{path}")
            continue
        try:
            path.read_bytes()
        except OSError as error:
            report.problems.append(f"字体映射不可读：{path}（{error}）")

    if roundtrip:
        for game_key in GAME_ORDER:
            if game_key not in corpus.games:
                continue
            path = source_ucs(GAMES[game_key])
            try:
                original = path.read_bytes()
                rebuilt = roundtrip_bytes(original)
            except (OSError, UcsError) as error:
                report.problems.append(f"{path} 无法往返：{error}")
                continue
            if rebuilt != original:
                report.problems.append(f"{path} 解包/打包后字节不一致")

    return report
