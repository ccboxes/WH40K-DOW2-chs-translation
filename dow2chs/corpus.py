"""加载两份英文原版，并建立 key/text 索引。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .games import GAME_ORDER, GAMES, Game, source_ucs
from .ucs import Entry, UcsError, load, sha256_file


class SourceError(ValueError):
    """英文原版不完整或与预期不一致。"""


@dataclass
class Corpus:
    games: dict[str, list[Entry]] = field(default_factory=dict)
    key_to_text: dict[str, str] = field(default_factory=dict)
    text_to_keys: dict[str, list[str]] = field(default_factory=dict)
    unique_texts: list[str] = field(default_factory=list)
    source_hashes: dict[str, str] = field(default_factory=dict)

    def all_keys(self) -> set[str]:
        return set(self.key_to_text)

    def keys_for(self, games: tuple[str, ...]) -> set[str]:
        result: set[str] = set()
        for game in games:
            result.update(entry.key for entry in self.games[game])
        return result


def load_corpus(
    game_keys: tuple[str, ...] = GAME_ORDER,
    *,
    check_counts: bool = True,
) -> Corpus:
    corpus = Corpus()

    for game_key in game_keys:
        game = GAMES[game_key]
        path = source_ucs(game)
        if not path.exists():
            raise SourceError(
                f"缺少英文原版：{path}\n先运行 python -m dow2chs source sync"
            )
        try:
            document = load(path, strict_source=True)
        except UcsError as error:
            raise SourceError(f"{path} 无法解析：{error}") from error

        if check_counts and len(document.entries) != game.expected_keys:
            raise SourceError(
                f"{path} 有 {len(document.entries)} 个 key，预期 {game.expected_keys}。"
                "游戏更新后请先核对来源并更新 games.py。"
            )

        keys = [entry.key for entry in document.entries]
        if len(keys) != len(set(keys)):
            raise SourceError(f"{path} 存在重复 key")

        corpus.games[game_key] = document.entries
        corpus.source_hashes[game_key] = sha256_file(path)

    for game_key in game_keys:
        for entry in corpus.games[game_key]:
            existing = corpus.key_to_text.get(entry.key)
            if existing is not None and existing != entry.text:
                raise SourceError(
                    f"key {entry.key} 在两份原版中的英文不同，不能共用译文"
                )
            corpus.key_to_text[entry.key] = entry.text

    seen_texts: set[str] = set()
    for game_key in game_keys:
        for entry in corpus.games[game_key]:
            keys = corpus.text_to_keys.setdefault(entry.text, [])
            if entry.key not in keys:
                keys.append(entry.key)
            if entry.text not in seen_texts:
                seen_texts.add(entry.text)
                corpus.unique_texts.append(entry.text)

    return corpus


def source_rows(game: Game) -> list[Entry]:
    return load_corpus((game.key,)).games[game.key]


def source_path(game: Game) -> Path:
    return source_ucs(game)
