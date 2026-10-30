"""格式符、标签与译文校验。

DOW2 的占位符有两种形态：
- ``%1NAME%``、``%N%`` 这类变量；
- ``%%`` 表示一个字面百分号。

因此 ``%1CHANCE%%%`` 是一个变量加一个字面百分号，不能误解析。

尖括号标签（``<chuckle>``、``<Whisper From: %1PLAYERNAME%>``）分两类：
- ``<br>`` 是引擎标记，必须原样保留；
- 其余是舞台提示或界面前缀，标签内文字可译，标签本身不能删改。
"""

from __future__ import annotations

import re
from collections import Counter

# %% 优先；否则匹配 %1NAME%、%N%、%1Campaign name% 这类变量。
# 变量内容只允许字母、数字、下划线，以及词间的空格/连字符；不能跨句号、
# 逗号等标点，否则原文里的 "35%. ... 15%." 会被误当成一个变量。
# %i 是少数由引擎直接解释的 printf 占位符，没有收尾的 %。
PLACEHOLDER_RE = re.compile(
    r"%(?:%|[0-9]*[A-Za-z][A-Za-z0-9_]*(?:[ -][A-Za-z0-9_]+)*[ \t]*%)"
    r"|%i(?![A-Za-z])"
)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
LETTER_RE = re.compile(r"[A-Za-z]")
# 成对的尖括号标签/提示，如 <chuckle>、<%1PLAYERNAME%>、<br>。
ANGLE_RE = re.compile(r"<[^<>\r\n]*>")


def placeholders(text: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for match in PLACEHOLDER_RE.finditer(text):
        counter[match.group(0)] += 1
    # <br> 是唯一在文本里当标记使用的尖括号标签；其余 <Scream> 等是舞台提示。
    for match in BR_RE.finditer(text):
        counter["<br>"] += 1
    return counter


def has_letters(text: str) -> bool:
    return LETTER_RE.search(text) is not None


def angle_groups(text: str) -> list[str]:
    """返回所有成对尖括号的内容（不含 ``<>`` 本身）。

    ``<chuckle>``、``<%1PLAYERNAME%>`` 这类标签的内容是普通文本，可以翻译；
    这里只关心标签的存在与标签内的变量，不比较内容本身。
    """
    return ANGLE_RE.findall(text)


def stray_angles(text: str) -> tuple[int, int]:
    """返回成对标签之外的孤立 ``<`` 和 ``>`` 数量。

    原版里有把 ``<`` 当“小于”用的文本（如 ``< One bar``）和倒置的
    ``>ptah<``，所以不能要求所有尖括号都成对，只能要求与原文一致。
    """
    rest = ANGLE_RE.sub("", text)
    return rest.count("<"), rest.count(">")


def _format_counter(counter: Counter[str]) -> str:
    return ", ".join(f"{token}x{count}" for token, count in sorted(counter.items()))


def _format_groups(groups: list[str]) -> str:
    preview = "、".join(f"<{group}>" for group in groups[:5])
    if len(groups) > 5:
        preview += "…"
    return preview


def _check_angle_groups(source: str, translation: str) -> list[str]:
    """标签内容可译，但标签个数与标签内的变量必须与原文一致。"""
    expected = angle_groups(source)
    actual = angle_groups(translation)

    if len(expected) != len(actual):
        details = f"原文 {len(expected)} 个：{_format_groups(expected)}"
        if not expected:
            details = "原文没有尖括号标签"
        return [
            f"尖括号标签数量不一致（{details}；译文 {len(actual)} 个："
            f"{_format_groups(actual) or '无'}）"
        ]

    errors: list[str] = []
    for index, (expected_group, actual_group) in enumerate(
        zip(expected, actual), start=1
    ):
        expected_tokens = placeholders(expected_group)
        actual_tokens = placeholders(actual_group)
        if expected_tokens != actual_tokens:
            errors.append(
                f"第 {index} 个尖括号 <{expected_group}> 内的变量不一致"
                f"（原文 {_format_counter(expected_tokens) or '无'}；"
                f"译文 <{actual_group}> 为 {_format_counter(actual_tokens) or '无'}）"
            )
    return errors


def validate_translation(source: str, translation: str) -> tuple[list[str], list[str]]:
    """返回 (错误, 警告)。错误会阻止生成，警告只报告。"""
    errors: list[str] = []
    warnings: list[str] = []

    if translation == "":
        errors.append("译文为空")
        return errors, warnings

    if "\r" in translation:
        errors.append("译文含 CR（会破坏 UCS 行结构）")

    expected = placeholders(source)
    actual = placeholders(translation)
    if expected != actual:
        missing = expected - actual
        extra = actual - expected
        details = []
        if missing:
            details.append(f"缺少 {_format_counter(missing)}")
        if extra:
            details.append(f"多出 {_format_counter(extra)}")
        errors.append("格式符不一致：" + "；".join(details))

    if source.count("%") != translation.count("%"):
        errors.append(
            f"百分号数量不一致（原文 {source.count('%')}，译文 {translation.count('%')}）"
        )

    source_tabs = source.count("\t")
    target_tabs = translation.count("\t")
    if source_tabs != target_tabs:
        errors.append(f"TAB 数量不一致（原文 {source_tabs}，译文 {target_tabs}）")

    errors.extend(_check_angle_groups(source, translation))
    source_stray = stray_angles(source)
    target_stray = stray_angles(translation)
    if source_stray != target_stray:
        warnings.append(
            "未成对的尖括号与原文不一致"
            f"（原文 < x{source_stray[0]}、> x{source_stray[1]}；"
            f"译文 < x{target_stray[0]}、> x{target_stray[1]}）"
        )

    if source[:1].isspace() != translation[:1].isspace():
        warnings.append("行首空白与原文不一致")
    if source[-1:].isspace() != translation[-1:].isspace():
        warnings.append("行尾空白与原文不一致")

    return errors, warnings


def restore_edge_whitespace(source: str, translation: str) -> str:
    """把原文的行首/行尾空白补回译文，避免布局被翻译器 trim 掉。"""
    if translation == "":
        return translation

    leading = re.match(r"^\s*", source)
    if leading and leading.group(0) and not translation[:1].isspace():
        translation = leading.group(0) + translation

    trailing = re.search(r"\s*$", source)
    if trailing and trailing.group(0) and not translation[-1:].isspace():
        translation = translation + trailing.group(0)

    return translation
