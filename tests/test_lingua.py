from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dow2chs.corpus import Corpus
from dow2chs.lingua import export_lingua, import_lingua
from dow2chs.ucs import Entry


def make_corpus() -> Corpus:
    dow2 = [Entry("1", "Hello"), Entry("2", "Hello"), Entry("3", "World")]
    retribution = [
        Entry("1", "Hello"),
        Entry("2", "Hello"),
        Entry("3", "World"),
        Entry("4", "Armor "),
    ]
    text_to_keys: dict[str, list[str]] = {}
    key_to_text = {}
    unique = []
    for entry in dow2 + retribution:
        key_to_text[entry.key] = entry.text
        text_to_keys.setdefault(entry.text, [])
        if entry.key not in text_to_keys[entry.text]:
            text_to_keys[entry.text].append(entry.key)
        if entry.text not in unique:
            unique.append(entry.text)
    return Corpus(
        games={"dow2": dow2, "retribution": retribution},
        key_to_text=key_to_text,
        text_to_keys=text_to_keys,
        unique_texts=unique,
        source_hashes={"dow2": "a", "retribution": "b"},
    )


class LinguaTests(unittest.TestCase):
    def test_export_deduplicates_and_import_maps_all_keys(self) -> None:
        corpus = make_corpus()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "input"
            report = export_lingua(corpus, {}, out)
            self.assertEqual(report.exported_texts, 3)
            exported = json.loads((out / "dow2-retribution.json").read_text(encoding="utf-8"))
            self.assertEqual(exported, {"Hello": "", "World": "", "Armor ": ""})

            catalog_path = Path(directory) / "catalog.ndjson"
            translations = {"1": "旧译文"}
            output = Path(directory) / "translated.json"
            output.write_text(
                json.dumps({"Hello": "你好", "World": "世界", "Armor ": "护甲"}, ensure_ascii=False),
                encoding="utf-8",
            )
            result = import_lingua(
                output,
                corpus,
                translations,
                catalog_path=catalog_path,
            )
            self.assertFalse(result.has_problems)
            self.assertEqual(translations["1"], "你好")
            self.assertEqual(translations["2"], "你好")
            self.assertEqual(translations["3"], "世界")
            self.assertEqual(translations["4"], "护甲 ")
            self.assertEqual(result.updated_keys, 4)

    def test_invalid_placeholder_is_reported_and_not_saved(self) -> None:
        corpus = Corpus(
            games={"retribution": [Entry("1", "%1NAME% wins")]},
            key_to_text={"1": "%1NAME% wins"},
            text_to_keys={"%1NAME% wins": ["1"]},
            unique_texts=["%1NAME% wins"],
            source_hashes={"retribution": "x"},
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "translated.json"
            output.write_text(
                json.dumps({"%1NAME% wins": "胜利"}, ensure_ascii=False),
                encoding="utf-8",
            )
            catalog_path = Path(directory) / "catalog.ndjson"
            translations: dict[str, str] = {}
            result = import_lingua(
                output, corpus, translations, catalog_path=catalog_path
            )
            self.assertTrue(result.has_problems)
            self.assertEqual(translations, {})
            self.assertFalse(catalog_path.exists())

    def test_nonletter_same_text_is_accepted(self) -> None:
        corpus = Corpus(
            games={"retribution": [Entry("1", "100%")]},
            key_to_text={"1": "100%"},
            text_to_keys={"100%": ["1"]},
            unique_texts=["100%"],
            source_hashes={"retribution": "x"},
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "translated.json"
            output.write_text(json.dumps({"100%": "100%"}), encoding="utf-8")
            translations: dict[str, str] = {}
            result = import_lingua(
                output,
                corpus,
                translations,
                catalog_path=Path(directory) / "catalog.ndjson",
            )
            self.assertFalse(result.has_problems)
            self.assertEqual(translations, {"1": "100%"})

    def test_format_only_with_named_variables_is_accepted(self) -> None:
        source = "%1X%.%2Y%"
        corpus = Corpus(
            games={"retribution": [Entry("1", source)]},
            key_to_text={"1": source},
            text_to_keys={source: ["1"]},
            unique_texts=[source],
            source_hashes={"retribution": "x"},
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "translated.json"
            output.write_text(json.dumps({source: source}), encoding="utf-8")
            translations: dict[str, str] = {}
            result = import_lingua(
                output,
                corpus,
                translations,
                catalog_path=Path(directory) / "catalog.ndjson",
            )
            self.assertFalse(result.has_problems)
            self.assertEqual(translations, {"1": source})

    def test_whitespace_only_source_is_accepted(self) -> None:
        corpus = Corpus(
            games={"retribution": [Entry("1", " ")]},
            key_to_text={"1": " "},
            text_to_keys={" ": ["1"]},
            unique_texts=[" "],
            source_hashes={"retribution": "x"},
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "translated.json"
            output.write_text(json.dumps({" ": " "}), encoding="utf-8")
            translations: dict[str, str] = {}
            result = import_lingua(
                output,
                corpus,
                translations,
                catalog_path=Path(directory) / "catalog.ndjson",
            )
            self.assertFalse(result.has_problems)
            self.assertEqual(translations, {"1": " "})

    def test_keep_existing_does_not_overwrite(self) -> None:
        corpus = make_corpus()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "translated.json"
            output.write_text(
                json.dumps({"Hello": "你好"}, ensure_ascii=False), encoding="utf-8"
            )
            translations = {"1": "已有", "2": "已有"}
            result = import_lingua(
                output,
                corpus,
                translations,
                keep_existing=True,
                catalog_path=Path(directory) / "catalog.ndjson",
            )
            self.assertEqual(translations["1"], "已有")
            self.assertEqual(result.kept_existing, 2)


if __name__ == "__main__":
    unittest.main()
