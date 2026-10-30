# WH40K-DOW2-chs-translation

《战锤 40K：战争黎明 2》周年纪念版与《报应》的简体中文汉化项目。

这是一个重新建立的项目。旧项目的译文质量不达标，因此这里不复用旧补丁的译文，而是从两份英文原版重新翻译，并把“解包、导出、导入、校验、打包、发版”做成可重复执行的流水线。

## 游戏文本

游戏的可翻译文本只有一份 UCS：

| 游戏 | 原版文件 | key 数 |
| --- | --- | --- |
| Dawn of War 2（含混沌崛起） | `Dawn of War 2\GameAssets\Locale\English\DOW2.ucs` | 50,695 |
| Dawn of War II - Retribution | `Dawn of War II - Retribution\GameAssets\Locale\English\DOW2.ucs` | 71,720 |

- 报应版是周年纪念版的超集；两者共有的 key 英文完全一致，另有 43 个 key 只存在于周年纪念版。
- 合并去重后共有 71,763 个 key、45,910 条不同英文原文。
- 两份成品仍然分开生成：成品 A 的 key 集合与周年纪念版原版完全一致，成品 B 与报应版完全一致。
- `.sga` 文件装的是语音；`.lua` 过场脚本只通过 `locId` 引用 UCS。不要把它们当作文本资源。
- `font_mapping.ini` 是中文显示所需的字体映射，不属于 UCS，但必须和 UCS 一起发布。

UCS 格式：

- UTF-16LE + BOM + CRLF；
- 每行 `key<TAB>text`；
- `text` 内可能还有 TAB、尾随空格，少数条目内嵌孤立 LF；
- 因此只能按 CRLF 拆行，不能用 `splitlines()` 或文本模式读写。

## 目录

```text
data/source/             英文原版（只读，附 SHA256SUMS）
data/catalog/            译本目录 translations.ndjson（按数字 key 排序）
data/glossary/           LinguaGacha 术语表源文件 glossary.tsv
data/font_mapping/       两份中文 font_mapping.ini
data/font_patch/         报应中文字体包 zz_font.sga 与安装脚本
dow2chs/                 纯标准库 Python 包
tests/                   unittest
work/                    解包结果、LinguaGacha 输入/输出（不提交）
build/                   生成的补丁目录（不提交）
dist/                    发布 zip 与 sha256（不提交）
```

`data/source` 和 `data/font_mapping` 是构建输入，不要手改。要改译文，只改 `data/catalog/translations.ndjson`。

## 环境

- Windows + Python 3.9 及以上；
- Git for Windows；
- 无第三方 Python 依赖，无需安装包；
- 在本项目里，OpenCode 的 shell 后端已设为 `C:\Program Files\Git\bin\bash.exe`，不是 WSL。

在仓库根目录运行所有命令。

## 快速流程

### 1. 同步并自检英文原版

```sh
python -m dow2chs source sync
python -m dow2chs check
```

`source sync` 会从两个 Steam 安装目录复制原版并写入 `data/source/SHA256SUMS`。安装目录不同时，用环境变量覆盖：

```sh
DOW2_INSTALL="D:/Game/.../Dawn of War 2" \
DOW2_RETRIBUTION_INSTALL="D:/Game/.../Dawn of War II - Retribution" \
python -m dow2chs source sync
```

也接受 Git Bash 的 `/d/Game/...` 写法。

### 2. 导出 LinguaGacha 输入

```sh
python -m dow2chs export
```

输出：

```text
work/lingua/input/dow2-retribution.json    KV-JSON：{英文原文: 已有译文或空串}
work/lingua/input/glossary.json            术语表
work/lingua/input/manifest.json            来源哈希与统计
work/lingua/input/README.txt               给翻译者的说明
```

导出使用 LinguaGacha 原生的 `KV-JSON` 格式，并按英文原文去重：同一句英文只出现一次，所有使用这句话的 key 共用译文。这样既省 token，也避免同一句话被翻译成多个版本。

只导出其中一个游戏：

```sh
python -m dow2chs export --game dow2
python -m dow2chs export --game retribution
```

### 3. 在 LinguaGacha 中翻译

1. 把 `work/lingua/input/dow2-retribution.json` 拖进 LinguaGacha。
2. 原文语言选 English，译文语言选中文（简体）。
3. 在术语表页面导入 `work/lingua/input/glossary.json`。
4. 依次做术语提取、全文翻译、自动审校。
5. 用“生成译文”导出结果。不要改 JSON 的 key；key 是英文原文，不是数字 ID。

建议在 LinguaGacha 里对 `%1NAME%`、`%1CHANCE%%%` 这类格式符开启文本保护，并在导出后由本项目的校验兜底。

### 4. 导回译文

```sh
python -m dow2chs import work/lingua/output/<输出文件>.json
python -m dow2chs catalog stats
```

导入时：

- 只接受能对应到英文原文的 key；
- 自动把原文的行首/行尾空白补回译文；
- 拒绝格式符不一致、TAB 数量不一致、含 CR、空译文的条目；
- 默认跳过“译文与英文完全相同”的条目；纯数字/格式符条目会自动接受；
- 确实要保留英文的专名，用 `--accept-same` 或：

```sh
python -m dow2chs catalog accept 12345 67890
```

如果只想补齐缺失条目、不覆盖已有译文：

```sh
python -m dow2chs import <输出文件> --keep-existing
```

### 5. 生成补丁

开发时允许缺失译文，缺失部分保留英文：

```sh
python -m dow2chs build
```

发布前必须严格检查（要求每个 key 都有译文）：

```sh
python -m dow2chs build --strict
```

输出：

```text
build/v<版本>/
├─ Dawn of War 2/GameAssets/Locale/English/{DOW2.ucs,font_mapping.ini}
├─ Dawn of War II - Retribution/
│  ├─ GameAssets/Locale/English/{DOW2.ucs,font_mapping.ini}
│  ├─ GameAssets/Archives/zz_font.sga
│  ├─ install_font.bat
│  └─ install_font.ps1
├─ manifest.json
└─ README.txt
```

两份 UCS 都按各自原版的行顺序逐行写出；key 集合、行数、行顺序和结尾 CRLF 与原版一致。

《报应》原版缺少 `tchinese.gfx` 字体包，只有 `font_mapping.ini` 仍会显示方框。构建会把 `data/font_patch/retribution/zz_font.sga` 放进补丁，并附带 `install_font.bat`；安装后必须运行一次该脚本，它会备份 `DOW2.module` 并把字体包注册到 `[data:common]`。

### 6. 版本与发布

```sh
python -m dow2chs version set 0.1.0
# 编辑 CHANGELOG.md，把## [0.1.0] 的内容写清楚
python -m dow2chs release
```

`release` 会做严格构建，生成：

```text
dist/WH40K-DOW2-chs-v0.1.0.zip
dist/WH40K-DOW2-chs-v0.1.0.zip.sha256
```

zip 里直接就是两个游戏文件夹，解压到 Steam 的 `common` 目录即可覆盖；随后进入《报应》目录运行一次 `install_font.bat`，把 `zz_font.sga` 注册进 `DOW2.module`。发版后自行打 tag：

```sh
git tag -a v0.1.0 -m "v0.1.0"
git push --tags
```

## 解包 / 打包

UCS 可以无损转成 JSON，便于审阅、对比和外部工具处理：

```sh
python -m dow2chs unpack --game retribution -o work/retribution.ucs.json
python -m dow2chs pack work/retribution.ucs.json -o work/retribution.ucs
```

JSON 结构：

```json
{
  "schema": "dow2-ucs/1",
  "encoding": "utf-16-le",
  "bom": true,
  "final_newline": true,
  "entries": [
    { "key": "1", "text": "..." }
  ]
}
```

`unpack`/`pack` 保留 BOM、末尾换行、TAB、孤立 LF 和尾随空格；对原版做一次往返应得到逐字节相同的文件。

## 校验规则

`check` 和 `build` 会检查：

- 两份原版的 SHA256 与 key 数；
- 译本目录的 key 必须存在于原版；
- `%1NAME%`、`%N%`、`%%` 等格式符的数量和顺序；
- `<br>` 标记；
- 尖括号标签的数量，以及标签内的变量（`<chuckle>`、`<Whisper From: %1PLAYERNAME%>` 的标签内容可译，标签本身不能删或改）；
- TAB 数量；
- 不允许 CR（会破坏 UCS 行结构）；
- 百分号数量；
- 译文不能为空；
- 原版解包再打包后必须逐字节一致。

特别注意：`%1CHANCE%%%` 是“变量 + 字面百分号”，不能写成 `%1CHANCE%`。

## 版本管理

- `VERSION`：当前版本，SemVer；
- `CHANGELOG.md`：每个版本的变更；
- `python -m dow2chs version set X.Y.Z`：更新 VERSION，并把 Unreleased 内容移到新版本标题下；
- `python -m dow2chs release`：严格构建 + 生成 zip + 生成 sha256，不自动提交、不自动打 tag；
- `build/`、`dist/`、`work/` 都是生成物，已在 `.gitignore` 中。

## 版权

游戏文本与字体资源版权归 Relic Entertainment / SEGA 所有。本仓库只保存英文原文用于翻译对照；发布物包含翻译文本、字体映射，以及《报应》所需的 `tchinese.gfx` 字体包。使用 LinguaGacha 时请遵守其项目说明，并在发布页注明使用了 LinguaGacha。
