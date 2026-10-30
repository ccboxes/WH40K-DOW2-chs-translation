from __future__ import annotations

import shutil
import unittest

from dow2chs.build import BuildError, build_patch
from dow2chs.corpus import Corpus
from dow2chs.paths import BUILD_DIR, ROOT
from dow2chs.ucs import Entry, load


def make_corpus() -> Corpus:
    dow2 = [Entry("1", "Hello"), Entry("2", "World")]
    retribution = [Entry("1", "Hello"), Entry("2", "World"), Entry("3", "New")]
    return Corpus(
        games={"dow2": dow2, "retribution": retribution},
        key_to_text={"1": "Hello", "2": "World", "3": "New"},
        text_to_keys={"Hello": ["1"], "World": ["2"], "New": ["3"]},
        unique_texts=["Hello", "World", "New"],
        source_hashes={"dow2": "a", "retribution": "b"},
    )


class BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = BUILD_DIR / "test-unit"
        if self.output.exists():
            shutil.rmtree(self.output)

    def tearDown(self) -> None:
        if self.output.exists():
            shutil.rmtree(self.output)

    def test_build_writes_both_games_with_expected_keys(self) -> None:
        corpus = make_corpus()
        translations = {"1": "你好", "2": "世界", "3": "新增"}
        result = build_patch(corpus, translations, "0.0.0-test", self.output, strict=True)
        self.assertEqual(result.games["dow2"].keys, 2)
        self.assertEqual(result.games["retribution"].keys, 3)

        dow2 = load(
            self.output
            / "Dawn of War 2"
            / "GameAssets"
            / "Locale"
            / "English"
            / "DOW2.ucs",
            strict_source=True,
        )
        self.assertEqual([entry.text for entry in dow2.entries], ["你好", "世界"])

        retribution_root = self.output / "Dawn of War II - Retribution"
        self.assertTrue(
            (retribution_root / "GameAssets" / "Archives" / "zz_font.sga").is_file()
        )
        self.assertTrue((retribution_root / "install_font.bat").is_file())
        self.assertTrue((retribution_root / "install_font.ps1").is_file())

    def test_strict_build_rejects_missing_translation(self) -> None:
        corpus = make_corpus()
        with self.assertRaises(BuildError):
            build_patch(corpus, {"1": "你好"}, "0.0.0-test", self.output, strict=True)

    def test_bad_placeholder_rejects_build(self) -> None:
        corpus = Corpus(
            games={"retribution": [Entry("1", "%1NAME% wins")]},
            key_to_text={"1": "%1NAME% wins"},
            text_to_keys={"%1NAME% wins": ["1"]},
            unique_texts=["%1NAME% wins"],
            source_hashes={"retribution": "b"},
        )
        with self.assertRaises(BuildError):
            build_patch(
                corpus,
                {"1": "胜利"},
                "0.0.0-test",
                self.output,
                strict=False,
            )

    def test_refuses_output_outside_repo(self) -> None:
        corpus = make_corpus()
        with self.assertRaises(BuildError):
            build_patch(corpus, {}, "0.0.0-test", ROOT.parent / "outside", strict=False)


if __name__ == "__main__":
    unittest.main()
