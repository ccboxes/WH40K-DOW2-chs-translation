from __future__ import annotations

import unittest

from dow2chs.text import (
    placeholders,
    restore_edge_whitespace,
    validate_translation,
)


class TextTests(unittest.TestCase):
    def test_literal_percent_and_placeholder(self) -> None:
        tokens = placeholders("%1CHANCE%%% chance")
        self.assertEqual(tokens["%1CHANCE%"], 1)
        self.assertEqual(tokens["%%"], 1)

    def test_missing_literal_percent_is_an_error(self) -> None:
        errors, _ = validate_translation("%1CHANCE%%% chance", "%1CHANCE% 几率")
        self.assertTrue(any("格式符" in error for error in errors))

    def test_literal_percent_must_be_preserved(self) -> None:
        errors, _ = validate_translation("100% complete", "100 完成")
        self.assertTrue(any("百分号" in error for error in errors))

    def test_literal_percent_pair_is_not_a_placeholder(self) -> None:
        source = "Reduces damage by 35%. Additional auras reduce it by 15%."
        translation = "使伤害降低35%。额外的光环可使其再降低15%。"
        errors, _ = validate_translation(source, translation)
        self.assertEqual(errors, [])

    def test_printf_percent_i_is_preserved(self) -> None:
        errors, _ = validate_translation("%i.%i GB", "%i.%i GB")
        self.assertEqual(errors, [])
        errors, _ = validate_translation("%i.%i GB", "0.0 GB")
        self.assertTrue(any("格式符" in error for error in errors))

    def test_repeated_placeholders_are_counted(self) -> None:
        errors, _ = validate_translation("%1NAME% met %1NAME%", "%1NAME% 遇到 %1NAME%")
        self.assertEqual(errors, [])

    def test_tab_mismatch_is_an_error(self) -> None:
        errors, _ = validate_translation("•\tReduce armor", "• 降低护甲")
        self.assertTrue(any("TAB" in error for error in errors))

    def test_br_tag_is_preserved(self) -> None:
        errors, _ = validate_translation("a<br>b", "甲<br>乙")
        self.assertEqual(errors, [])
        errors, _ = validate_translation("a<br>b", "甲乙")
        self.assertTrue(errors)

    def test_stage_direction_can_be_translated(self) -> None:
        errors, warnings = validate_translation(
            "<chuckle> It will be over soon.", "<轻笑> 用不了多久就结束了。"
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_dropped_stage_direction_is_an_error(self) -> None:
        errors, _ = validate_translation("<chuckle> It will be over soon.", "用不了多久。")
        self.assertTrue(any("尖括号" in error for error in errors))

    def test_invented_bracket_is_an_error(self) -> None:
        errors, _ = validate_translation("<Scream>", "（嚎叫）")
        self.assertTrue(any("尖括号" in error for error in errors))

    def test_reordered_stage_direction_is_allowed(self) -> None:
        errors, _ = validate_translation("<chuckle> Too easy.", "太简单了。<轻笑>")
        self.assertEqual(errors, [])

    def test_chat_prefix_keeps_variables(self) -> None:
        errors, _ = validate_translation(
            "<Whisper From: %1PLAYERNAME%>: %2CHATMESSAGE%",
            "<来自%1PLAYERNAME%的悄悄话>：%2CHATMESSAGE%",
        )
        self.assertEqual(errors, [])

    def test_changed_variable_inside_bracket_is_an_error(self) -> None:
        errors, _ = validate_translation(
            "<Whisper From: %1PLAYERNAME%>: %2CHATMESSAGE%",
            "<来自%1NAME%的悄悄话>：%2CHATMESSAGE%",
        )
        self.assertTrue(any("变量" in error for error in errors))

    def test_unbalanced_angle_matches_source(self) -> None:
        errors, warnings = validate_translation("< One bar", "< 一格")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_dropped_unbalanced_angle_only_warns(self) -> None:
        errors, warnings = validate_translation("< One bar", "少于一格")
        self.assertEqual(errors, [])
        self.assertTrue(any("尖括号" in warning for warning in warnings))

    def test_reversed_angles_are_preserved(self) -> None:
        errors, warnings = validate_translation(
            "YOU'S NO'FINK NO'FINK! >ptah<", "你这没用的东西！>ptah<"
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_restore_edge_whitespace(self) -> None:
        self.assertEqual(restore_edge_whitespace("  hello  ", "你好"), "  你好  ")
        self.assertEqual(restore_edge_whitespace("hello", "你好"), "你好")
        self.assertEqual(restore_edge_whitespace("hello\n", "你好"), "你好\n")


if __name__ == "__main__":
    unittest.main()
