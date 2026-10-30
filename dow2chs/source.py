"""从游戏安装同步英文原版，并校验其完整性。"""

from __future__ import annotations

import hashlib

from .games import GAMES, Game, install_ucs, source_ucs
from .io_utils import write_text_exact
from .paths import SOURCE_DIR
from .ucs import UcsError, load, sha256_file

CHECKSUM_PATH = SOURCE_DIR / "SHA256SUMS"


class SyncError(ValueError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sync(allow_count_change: bool = False) -> list[tuple[Game, int, str]]:
    results: list[tuple[Game, int, str]] = []
    for game in GAMES.values():
        origin = install_ucs(game)
        if not origin.exists():
            raise SyncError(
                f"找不到游戏原版：{origin}\n"
                f"可用环境变量 {game.install_env} 指定安装目录。"
            )

        data = origin.read_bytes()
        try:
            document = load(origin, strict_source=True)
        except UcsError as error:
            raise SyncError(f"{origin} 无法解析：{error}") from error

        if not allow_count_change and len(document.entries) != game.expected_keys:
            raise SyncError(
                f"{origin} 有 {len(document.entries)} 个 key，"
                f"预期 {game.expected_keys}。确认是游戏更新后，"
                "请更新 dow2chs/games.py 并加 --allow-count-change 重新同步。"
            )

        destination = source_ucs(game)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        results.append((game, len(document.entries), _sha256_bytes(data)))

    write_checksums()
    return results


def write_checksums() -> None:
    lines = []
    for game in GAMES.values():
        path = source_ucs(game)
        if not path.exists():
            raise SyncError(f"缺少英文原版：{path}")
        relative = path.relative_to(SOURCE_DIR).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    write_text_exact(CHECKSUM_PATH, "\n".join(lines) + "\n")


def verify() -> list[str]:
    problems: list[str] = []
    if not CHECKSUM_PATH.exists():
        return [f"缺少校验文件：{CHECKSUM_PATH}"]

    lines = CHECKSUM_PATH.read_text(encoding="utf-8").splitlines()
    expected: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2:
            problems.append(f"校验文件格式错误：{line!r}")
            continue
        expected[parts[1]] = parts[0]

    for game in GAMES.values():
        relative = source_ucs(game).relative_to(SOURCE_DIR).as_posix()
        path = SOURCE_DIR / relative
        if not path.exists():
            problems.append(f"缺少文件：{relative}")
            continue
        if relative not in expected:
            problems.append(f"校验文件没有记录：{relative}")
            continue
        actual = sha256_file(path)
        if actual != expected[relative]:
            problems.append(f"哈希不一致：{relative}")

    return problems


def verify_install_matches_source() -> list[str]:
    problems: list[str] = []
    for game in GAMES.values():
        origin = install_ucs(game)
        local = source_ucs(game)
        if not origin.exists():
            problems.append(f"找不到游戏原版：{origin}")
            continue
        if not local.exists():
            problems.append(f"缺少本地原版：{local}")
            continue
        if sha256_file(origin) != sha256_file(local):
            problems.append(f"游戏原版与 data/source 不一致：{game.key}")
    return problems
