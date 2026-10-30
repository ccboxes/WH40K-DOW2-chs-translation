# data 目录说明

- `source/dow2/DOW2.ucs`、`source/retribution/DOW2.ucs`：从游戏安装复制的英文原版，只读。`SHA256SUMS` 由 `python -m dow2chs source sync` 生成。
- `catalog/translations.ndjson`：唯一可编辑的译文目录；一行一个 `{"key","text"}`。
- `glossary/glossary.tsv`：术语表源文件，制表符分隔：`英文<TAB>中文<TAB>备注`。运行 `export` 时生成 LinguaGacha 用的 `glossary.json`。
- `font_mapping/*/font_mapping.ini`：中文补丁使用的字体映射，来自已知可用的旧补丁；不要换成英文原版。
- `font_patch/retribution/`：《报应》中文字体包 `zz_font.sga` 与 `install_font.bat`/`install_font.ps1`。字体包从《战争黎明 2》的 `gamedefault.sga` 提取，构建时复制进发布目录。

这些文件都是构建输入，不要提交 `work/`、`build/`、`dist/`。
