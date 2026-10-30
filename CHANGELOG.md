# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)；版本号写在 `VERSION`。

## [Unreleased]

## [1.0.1] - 2026-10-30

### 修复

- 修复《报应》安装后文字全部显示为方框的问题：补丁现在附带 `tchinese.gfx` 字体包 `zz_font.sga`，并新增 `install_font.bat`，运行后会把字体包注册到 `DOW2.module` 的 `[data:common]` 段。
- 安装说明补充《报应》字体补丁的运行步骤。

## [1.0.0] - 2026-10-30

### 汉化

- 《战争黎明 2》与《报应》全部 50,695 / 71,720 个 key 完成简体中文翻译，覆盖率 100%。
- 统一术语：Typhon 堤丰、Nob 大只佬、Trukk / War Trukk 突突车、Shoota 突突枪、Slugga 小突枪、Slugga Boy 小突枪小子。
- 保留兽人语口语风格与角色语气，同时保留全部格式符、TAB、尖括号标签和首尾空白。
- 生成两份游戏的 UCS 汉化补丁与字体映射，可直接覆盖到游戏安装目录。

### Added

- 建立新的翻译流水线：UCS 解包/打包、LinguaGacha KV-JSON 导入导出、译本目录、严格构建与发布打包。
- 收录两份游戏英文原版，并加入 SHA256 校验。
- 加入格式符、TAB、换行与空白校验。
- 加入尖括号标签校验：`<chuckle>`、`<Whisper From: %1PLAYERNAME%>` 等标签的数量和标签内变量必须与原文一致，孤立 `<`/`>` 只报警告。

