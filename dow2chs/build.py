"""生成两份可直接覆盖安装的汉化文件。"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .corpus import Corpus
from .games import GAME_ORDER, GAMES, font_mapping, locale_dir
from .io_utils import write_text_exact
from .paths import CATALOG_PATH, ROOT
from .text import validate_translation
from .ucs import Entry, UcsDocument, load, save, sha256_file

FONT_PATCH_DIR = ROOT / "data" / "font_patch"


class BuildError(ValueError):
    def __init__(self, issues: list[str], warnings: list[str] | None = None) -> None:
        super().__init__("\n".join(issues))
        self.issues = issues
        self.warnings = warnings or []


@dataclass
class GameStats:
    keys: int
    translated: int
    missing: int
    same_as_source: int
    ucs_sha256: str
    ucs_bytes: int
    font_sha256: str


@dataclass
class BuildResult:
    version: str
    output_dir: Path
    games: dict[str, GameStats] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _guard_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT.resolve() or not resolved.is_relative_to(ROOT.resolve()):
        raise BuildError([f"拒绝写入输出目录：{resolved}"])
    protected = [
        ROOT / "data",
        ROOT / "dow2chs",
        ROOT / "tests",
        ROOT / ".git",
    ]
    for item in protected:
        target = item.resolve()
        if resolved == target or resolved.is_relative_to(target):
            raise BuildError([f"拒绝写入受保护目录：{resolved}"])


def _install_readme(version: str) -> str:
    return f"""WH40K-DOW2-chs-translation v{version}
=====================================

这是《战锤 40K：战争黎明 2》周年纪念版与《报应》的简体中文补丁。

安装
----
1. 先备份游戏原文件：
   Dawn of War 2\\GameAssets\\Locale\\English\\DOW2.ucs
   Dawn of War 2\\GameAssets\\Locale\\English\\font_mapping.ini
   Dawn of War II - Retribution\\GameAssets\\Locale\\English\\DOW2.ucs
   Dawn of War II - Retribution\\GameAssets\\Locale\\English\\font_mapping.ini
2. 把压缩包里的两个游戏文件夹直接解压到 Steam 的 common 目录，
   覆盖同名文件：
   ...\\steamapps\\common\\Dawn of War 2\\
   ...\\steamapps\\common\\Dawn of War II - Retribution\\
3. 《报应》还需要运行一次字体补丁：
   ...\\steamapps\\common\\Dawn of War II - Retribution\\install_font.bat
   它会备份 DOW2.module，并把 zz_font.sga 注册为中文字体包。
4. 启动游戏。若需要恢复英文，把备份文件覆盖回去。

说明
----
- 两份 DOW2.ucs 分别对应各自的原版：行数、key 顺序、结尾 CRLF 完全一致。
- 未翻译条目会保留英文，而不是写成 !数字 占位符。
- font_mapping.ini 使用 tchinese 字体，必须与原 UCS 一起覆盖。
- 《报应》原版没有 tchinese.gfx 字体包；zz_font.sga 补上了这个资源，
  install_font.bat 负责把它写入 DOW2.module 的 [data:common] 段。
- 如果 Steam 验证完整性或更新游戏，DOW2.module 可能被还原，重新运行
  install_font.bat 即可。
- manifest.json 记录了版本、源文件哈希和各文件哈希，可用于校验。

游戏文本与字体资源版权归 Relic Entertainment / SEGA 所有。
本补丁只分发翻译文本与必要的字体补丁文件。
"""


def build_patch(
    corpus: Corpus,
    translations: dict[str, str],
    version: str,
    output_dir: Path,
    *,
    strict: bool = False,
    catalog_path: Path = CATALOG_PATH,
) -> BuildResult:
    _guard_output(output_dir)

    issues: list[str] = []
    warnings: list[str] = []
    rendered: dict[str, list[Entry]] = {}
    pending_stats: dict[str, dict[str, int]] = {}

    if strict:
        unknown = sorted(set(translations) - corpus.all_keys(), key=int)
        if unknown:
            issues.append(
                f"译本目录有 {len(unknown)} 个原版不存在的 key，例如："
                + "、".join(unknown[:20])
            )

    for game_key in GAME_ORDER:
        if game_key not in corpus.games:
            continue
        game = GAMES[game_key]
        font = font_mapping(game)
        if not font.exists():
            issues.append(f"缺少字体映射：{font}")

        entries: list[Entry] = []
        translated = 0
        missing = 0
        same = 0
        placeholder_errors = 0

        for source_entry in corpus.games[game_key]:
            target = translations.get(source_entry.key)
            if target is None:
                missing += 1
                target = source_entry.text
            else:
                translated += 1

            if target == source_entry.text and source_entry.key in translations:
                same += 1

            errors, ghost_warnings = validate_translation(source_entry.text, target)
            if errors:
                placeholder_errors += 1
                if placeholder_errors <= 30:
                    issues.append(
                        f"{game_key} key {source_entry.key}："
                        + "；".join(errors)
                    )
            for warning in ghost_warnings:
                if len(warnings) < 30:
                    warnings.append(f"{game_key} key {source_entry.key}：{warning}")
            entries.append(Entry(key=source_entry.key, text=target))

        if placeholder_errors > 30:
            issues.append(
                f"{game_key} 共有 {placeholder_errors} 条格式校验失败，仅列出前 30 条"
            )
        if strict and missing:
            sample = [
                entry.key
                for entry in corpus.games[game_key]
                if entry.key not in translations
            ][:20]
            issues.append(
                f"{game_key} 缺少 {missing} 条译文（共 {len(entries)} 条），例如："
                + "、".join(sample)
                + "。运行 python -m dow2chs catalog stats 查看覆盖率。"
            )

        rendered[game_key] = entries
        pending_stats[game_key] = {
            "keys": len(entries),
            "translated": translated,
            "missing": missing,
            "same": same,
        }

    if issues:
        raise BuildError(issues, warnings)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = BuildResult(version=version, output_dir=output_dir, warnings=warnings)
    catalog_sha = sha256_file(catalog_path) if catalog_path.exists() else ""
    font_patch_files: dict[str, str] = {}

    for game_key, entries in rendered.items():
        game = GAMES[game_key]
        destination = output_dir / game.patch_dir / locale_dir(game)
        destination.mkdir(parents=True, exist_ok=True)
        ucs_path = destination / "DOW2.ucs"
        save(ucs_path, UcsDocument(entries=entries, has_bom=True, final_newline=True))

        reloaded = load(ucs_path, strict_source=True)
        if reloaded.entries != entries:
            raise BuildError([f"{ucs_path} 回读校验失败"])

        font_source = font_mapping(game)
        font_destination = destination / "font_mapping.ini"
        shutil.copyfile(font_source, font_destination)

        if game_key == "retribution":
            patch_source = FONT_PATCH_DIR / "retribution"
            patch_root = output_dir / game.patch_dir
            archives = patch_root / "GameAssets" / "Archives"
            archives.mkdir(parents=True, exist_ok=True)
            extra_files = (
                ("zz_font.sga", archives / "zz_font.sga"),
                ("install_font.bat", patch_root / "install_font.bat"),
                ("install_font.ps1", patch_root / "install_font.ps1"),
            )
            for name, target in extra_files:
                source = patch_source / name
                if not source.exists():
                    raise BuildError([f"缺少报应字体补丁文件：{source}"])
                shutil.copyfile(source, target)
                font_patch_files[target.relative_to(output_dir).as_posix()] = (
                    sha256_file(target)
                )

        stats = pending_stats[game_key]
        result.games[game_key] = GameStats(
            keys=stats["keys"],
            translated=stats["translated"],
            missing=stats["missing"],
            same_as_source=stats["same"],
            ucs_sha256=sha256_file(ucs_path),
            ucs_bytes=ucs_path.stat().st_size,
            font_sha256=sha256_file(font_destination),
        )

    manifest = {
        "name": "WH40K-DOW2-chs-translation",
        "version": version,
        "source_sha256": dict(corpus.source_hashes),
        "catalog_sha256": catalog_sha,
        "games": {
            game_key: {
                "title": GAMES[game_key].title,
                "install_dir": GAMES[game_key].patch_dir,
                "keys": stats.keys,
                "translated": stats.translated,
                "missing": stats.missing,
                "same_as_source": stats.same_as_source,
                "ucs_sha256": stats.ucs_sha256,
                "ucs_bytes": stats.ucs_bytes,
                "font_mapping_sha256": stats.font_sha256,
            }
            for game_key, stats in result.games.items()
        },
        "font_patch": {
            "install_dir": GAMES["retribution"].patch_dir,
            "files": font_patch_files,
        },
    }
    write_text_exact(
        output_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=4) + "\n",
    )
    write_text_exact(
        output_dir / "README.txt",
        _install_readme(version),
        newline="\r\n",
    )

    return result
