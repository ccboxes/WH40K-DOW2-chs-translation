"""两个游戏安装的元数据与路径解析。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .paths import FONT_DIR, SOURCE_DIR


@dataclass(frozen=True)
class Game:
    key: str
    title: str
    install_env: str
    default_install: str
    patch_dir: str
    expected_keys: int


GAMES: dict[str, Game] = {
    "dow2": Game(
        key="dow2",
        title="Dawn of War 2",
        install_env="DOW2_INSTALL",
        default_install=r"D:\Game\Steam\steamapps\common\Dawn of War 2",
        patch_dir="Dawn of War 2",
        expected_keys=50_695,
    ),
    "retribution": Game(
        key="retribution",
        title="Dawn of War II - Retribution",
        install_env="DOW2_RETRIBUTION_INSTALL",
        default_install=r"D:\Game\Steam\steamapps\common\Dawn of War II - Retribution",
        patch_dir="Dawn of War II - Retribution",
        expected_keys=71_720,
    ),
}

GAME_ORDER: tuple[str, ...] = ("dow2", "retribution")

_ALIASES = {
    "dow2": "dow2",
    "base": "dow2",
    "dawn of war 2": "dow2",
    "retribution": "retribution",
    "ret": "retribution",
    "dow2r": "retribution",
    "dow2_r": "retribution",
}


def resolve_game(name: str) -> Game:
    key = _ALIASES.get(name.strip().lower())
    if key is None:
        choices = "、".join(GAME_ORDER)
        raise ValueError(f"未知游戏 {name!r}，可选：{choices}")
    return GAMES[key]


def _normalize_override(value: str) -> str:
    """把 Git Bash 的 /d/Game/... 转成 Windows 可用的 D:/Game/...。"""
    if os.name == "nt":
        match = re.match(r"^/([A-Za-z])/(.*)$", value)
        if match:
            return f"{match.group(1).upper()}:/{match.group(2)}"
    return value


def install_root(game: Game) -> Path:
    override = os.environ.get(game.install_env)
    return Path(_normalize_override(override)) if override else Path(game.default_install)


def install_ucs(game: Game) -> Path:
    return install_root(game) / "GameAssets" / "Locale" / "English" / "DOW2.ucs"


def source_ucs(game: Game) -> Path:
    return SOURCE_DIR / game.key / "DOW2.ucs"


def font_mapping(game: Game) -> Path:
    return FONT_DIR / game.key / "font_mapping.ini"


def locale_dir(game: Game) -> Path:
    return Path("GameAssets") / "Locale" / "English"
