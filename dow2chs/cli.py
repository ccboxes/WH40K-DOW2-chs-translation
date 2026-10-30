"""命令行入口：python -m dow2chs <命令>。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import BuildError, build_patch
from .catalog import load_catalog, save_catalog
from .check import check_project
from .corpus import load_corpus
from .games import GAME_ORDER, GAMES, resolve_game, source_ucs
from .lingua import (
    export_lingua,
    find_output_file,
    import_lingua,
)
from .paths import BUILD_DIR, DIST_DIR, LINGUA_INPUT_DIR, WORK_DIR
from .release import release
from .source import sync, verify, verify_install_matches_source
from .text import validate_translation
from .ucsjson import pack_file, unpack_file
from .version import read_version, set_version


def _print_list(title: str, items: list[str], limit: int = 10) -> None:
    if not items:
        return
    print(f"{title}（{len(items)}）：")
    for item in items[:limit]:
        print(f"  - {item}")
    if len(items) > limit:
        print(f"  ... 还有 {len(items) - limit} 条")


def _print_problems(problems: list[str], limit: int = 10) -> None:
    _print_list("问题", problems, limit)


def _cmd_source_sync(args: argparse.Namespace) -> int:
    results = sync(allow_count_change=args.allow_count_change)
    for game, count, digest in results:
        print(f"{game.key}: {count} keys，sha256 {digest[:16]}… -> {source_ucs(game)}")
    mismatches = verify_install_matches_source()
    if mismatches:
        print("提示：本地 data/source 与当前安装不一致：")
        for item in mismatches:
            print(f"  - {item}")
    return 0


def _cmd_source_verify(args: argparse.Namespace) -> int:
    problems = verify()
    if args.install:
        problems += verify_install_matches_source()
    _print_problems(problems)
    if problems:
        return 1
    print("data/source 校验通过。")
    return 0


def _cmd_unpack(args: argparse.Namespace) -> int:
    if args.input:
        source = Path(args.input)
        stem = source.stem
    else:
        if not args.game:
            raise ValueError("unpack 需要 INPUT 或 --game")
        game = resolve_game(args.game)
        source = source_ucs(game)
        stem = game.key

    destination = Path(args.out) if args.out else WORK_DIR / f"{stem}.ucs.json"
    count = unpack_file(source, destination)
    print(f"已解包 {count} 条：{source} -> {destination}")
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    source = Path(args.input)
    destination = Path(args.out) if args.out else WORK_DIR / f"{source.stem}.ucs"
    count = pack_file(source, destination)
    print(f"已打包 {count} 条：{source} -> {destination}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    corpus = load_corpus()
    translations = load_catalog()
    game = args.game
    report = export_lingua(
        corpus,
        translations,
        Path(args.out) if args.out else LINGUA_INPUT_DIR,
        game=game,
        include_all=args.all,
    )
    print(f"目标：{report.target}，key {report.key_count} 条，唯一原文 {report.total_texts} 条")
    print(
        f"导出 {report.exported_texts} 条，预填 {report.prefilled_texts} 条，"
        f"已完成跳过 {report.skipped_complete} 条，冲突 {report.conflicting_texts} 条"
    )
    print(f"输出：{report.output}")
    print("把该文件拖进 LinguaGacha；翻译后运行 python -m dow2chs import <输出文件>")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    corpus = load_corpus()
    translations = load_catalog()
    before = len(translations)
    path = Path(args.path)
    if not path.exists():
        raise ValueError(f"路径不存在：{path}")

    output = find_output_file(path)
    report = import_lingua(
        output,
        corpus,
        translations,
        accept_same=args.accept_same,
        keep_existing=args.keep_existing,
        dry_run=args.dry_run,
    )
    after = len(translations)

    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}读取：{output}")
    print(
        f"{prefix}更新 {report.updated_keys} 个 key（{report.updated_texts} 条唯一原文），"
        f"目录 {before} -> {after} 条"
    )
    print(
        f"原文相同已接受 {report.accepted_same} 条，原文相同跳过 {len(report.skipped_same)} 条，"
        f"空译文 {len(report.empty)} 条，已有保留 {report.kept_existing} 条"
    )
    _print_list("原文相同但未接受", report.skipped_same, 5)
    _print_list("空译文", report.empty, 5)
    _print_list("未知原文", report.unknown, 5)
    if report.invalid:
        print(f"格式错误（{len(report.invalid)}）：")
        for source, errors in report.invalid[:10]:
            print(f"  - {source!r}: " + "；".join(errors))
        if len(report.invalid) > 10:
            print(f"  ... 还有 {len(report.invalid) - 10} 条")
    if report.warnings:
        print(f"空白警告（{len(report.warnings)}）：")
        for source, warnings in report.warnings[:5]:
            print(f"  - {source!r}: " + "；".join(warnings))

    return 1 if report.has_problems else 0


def _cmd_catalog_stats(args: argparse.Namespace) -> int:
    corpus = load_corpus()
    translations = load_catalog()
    unknown = sorted(set(translations) - corpus.all_keys(), key=int)

    print(f"译本目录：{len(translations)} 条，唯一原文 {len(corpus.unique_texts)} 条")
    for game_key in GAME_ORDER:
        if game_key not in corpus.games:
            continue
        entries = corpus.games[game_key]
        translated = sum(1 for entry in entries if entry.key in translations)
        percent = translated * 100.0 / len(entries) if entries else 0
        print(f"  {game_key}: {translated}/{len(entries)} = {percent:.2f}%")

    same = 0
    invalid = 0
    for key, text in translations.items():
        source = corpus.key_to_text.get(key)
        if source is None:
            continue
        if text == source:
            same += 1
        errors, _ = validate_translation(source, text)
        if errors:
            invalid += 1
    print(f"与英文完全相同：{same} 条；格式校验失败：{invalid} 条；未知 key：{len(unknown)} 条")
    _print_list("未知 key", unknown, 10)
    return 0


def _cmd_catalog_accept(args: argparse.Namespace) -> int:
    corpus = load_corpus()
    translations = load_catalog()
    changed = 0
    missing = []
    for key in args.keys:
        source = corpus.key_to_text.get(key)
        if source is None:
            missing.append(key)
            continue
        errors, _ = validate_translation(source, source)
        if errors:
            print(f"key {key} 无法直接接受英文：" + "；".join(errors))
            continue
        translations[key] = source
        changed += 1
    if changed:
        save_catalog(translations)
    print(f"已接受英文 {changed} 条。")
    _print_list("未知 key", missing, 10)
    return 1 if missing else 0


def _cmd_check(args: argparse.Namespace) -> int:
    report = check_project(roundtrip=not args.no_roundtrip)
    for game_key, (translated, total) in report.coverage.items():
        percent = translated * 100.0 / total if total else 0
        print(f"{game_key}: {translated}/{total} = {percent:.2f}%")
    _print_problems(report.problems)
    if report.warnings:
        _print_list("警告", report.warnings, 5)
    if report.problems:
        return 1
    print("自检通过。")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    version = read_version()
    corpus = load_corpus()
    translations = load_catalog()
    output = Path(args.out) if args.out else BUILD_DIR / f"v{version}"
    try:
        result = build_patch(
            corpus,
            translations,
            version,
            output,
            strict=args.strict,
        )
    except BuildError as error:
        _print_problems(error.issues)
        if error.warnings:
            _print_list("警告", error.warnings, 5)
        return 1

    for game_key, stats in result.games.items():
        print(
            f"{game_key}: {stats.keys} keys，已翻译 {stats.translated}，"
            f"缺失 {stats.missing}，生成 {stats.ucs_bytes} 字节"
        )
    if result.warnings:
        _print_list("警告", result.warnings, 5)
    print(f"输出：{result.output_dir}")
    return 0


def _cmd_version_show(args: argparse.Namespace) -> int:
    print(read_version())
    return 0


def _cmd_version_set(args: argparse.Namespace) -> int:
    set_version(args.version)
    print(f"VERSION -> {args.version}")
    print("请检查 CHANGELOG.md 的日期和内容。")
    return 0


def _cmd_release(args: argparse.Namespace) -> int:
    result = release(args.version)
    for game_key, stats in result.build.games.items():
        print(
            f"{game_key}: {stats.keys} keys，已翻译 {stats.translated}，"
            f"缺失 {stats.missing}"
        )
    print(f"发布包：{result.zip_path}")
    print(f"SHA256：{result.sha256}")
    print(f"校验文件：{DIST_DIR / (result.zip_path.name + '.sha256')}")
    print(f"下一步：git tag -a v{result.version} -m \"v{result.version}\"")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dow2chs",
        description="战锤 40K：战争黎明 2 简体中文汉化流水线",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    source_parser = sub.add_parser("source", help="同步/校验英文原版")
    source_sub = source_parser.add_subparsers(dest="source_command", required=True)
    sync_parser = source_sub.add_parser("sync", help="从游戏安装复制原版")
    sync_parser.add_argument("--allow-count-change", action="store_true")
    sync_parser.set_defaults(func=_cmd_source_sync)
    verify_parser = source_sub.add_parser("verify", help="校验 data/source")
    verify_parser.add_argument("--install", action="store_true", help="同时对比当前安装")
    verify_parser.set_defaults(func=_cmd_source_verify)

    unpack_parser = sub.add_parser("unpack", help="UCS -> JSON")
    unpack_parser.add_argument("input", nargs="?", help="UCS 路径；省略时用 --game")
    unpack_parser.add_argument("--game", choices=GAME_ORDER)
    unpack_parser.add_argument("-o", "--out")
    unpack_parser.set_defaults(func=_cmd_unpack)

    pack_parser = sub.add_parser("pack", help="JSON -> UCS")
    pack_parser.add_argument("input")
    pack_parser.add_argument("-o", "--out")
    pack_parser.set_defaults(func=_cmd_pack)

    export_parser = sub.add_parser("export", help="导出 LinguaGacha KV-JSON")
    export_parser.add_argument("--game", choices=GAME_ORDER)
    export_parser.add_argument("--all", action="store_true", help="包含已翻译条目")
    export_parser.add_argument("-o", "--out")
    export_parser.set_defaults(func=_cmd_export)

    import_parser = sub.add_parser("import", help="导入 LinguaGacha 译文")
    import_parser.add_argument("path", help="译文 JSON 或所在目录")
    import_parser.add_argument("--accept-same", action="store_true", help="接受与英文相同的译文")
    import_parser.add_argument("--keep-existing", action="store_true", help="不覆盖已有译文")
    import_parser.add_argument("--dry-run", action="store_true")
    import_parser.set_defaults(func=_cmd_import)

    catalog_parser = sub.add_parser("catalog", help="译本目录统计/操作")
    catalog_sub = catalog_parser.add_subparsers(dest="catalog_command", required=True)
    stats_parser = catalog_sub.add_parser("stats", help="覆盖率")
    stats_parser.set_defaults(func=_cmd_catalog_stats)
    accept_parser = catalog_sub.add_parser("accept", help="把指定 key 标记为保留英文")
    accept_parser.add_argument("keys", nargs="+")
    accept_parser.set_defaults(func=_cmd_catalog_accept)

    check_parser = sub.add_parser("check", help="项目自检")
    check_parser.add_argument("--no-roundtrip", action="store_true")
    check_parser.set_defaults(func=_cmd_check)

    build_parser_ = sub.add_parser("build", help="生成补丁目录")
    build_parser_.add_argument("--strict", action="store_true", help="要求 100%% 译文")
    build_parser_.add_argument("-o", "--out")
    build_parser_.set_defaults(func=_cmd_build)

    version_parser = sub.add_parser("version", help="版本号")
    version_sub = version_parser.add_subparsers(dest="version_command", required=True)
    show_parser = version_sub.add_parser("show")
    show_parser.set_defaults(func=_cmd_version_show)
    set_parser = version_sub.add_parser("set")
    set_parser.add_argument("version")
    set_parser.set_defaults(func=_cmd_version_set)

    release_parser = sub.add_parser("release", help="严格构建并打包 zip")
    release_parser.add_argument("--version")
    release_parser.set_defaults(func=_cmd_release)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
