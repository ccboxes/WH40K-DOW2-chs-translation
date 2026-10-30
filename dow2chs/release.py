"""打包发布物与版本管理。"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .build import BuildResult, build_patch
from .corpus import load_corpus
from .catalog import load_catalog
from .io_utils import write_text_exact
from .paths import BUILD_DIR, CATALOG_PATH, CHANGELOG_PATH, DIST_DIR
from .version import changelog_has_version, read_version


class ReleaseError(ValueError):
    pass


@dataclass
class ReleaseResult:
    version: str
    zip_path: Path
    sha256: str
    build: BuildResult


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def create_zip(source_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in source_dir.rglob("*") if path.is_file())
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            arcname = path.relative_to(source_dir).as_posix()
            archive.writestr(_zip_info(arcname), path.read_bytes())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release(version: str | None = None) -> ReleaseResult:
    current = read_version()
    if version is not None and version != current:
        raise ReleaseError(
            f"VERSION 是 {current}，与 --version {version} 不一致。"
            f"先运行 python -m dow2chs version set {version}"
        )
    version = current

    if not changelog_has_version(version, CHANGELOG_PATH):
        raise ReleaseError(
            f"CHANGELOG.md 没有 '## [{version}]' 标题。"
            "先补充变更记录，或运行 version set。"
        )

    corpus = load_corpus()
    translations = load_catalog()
    build_dir = BUILD_DIR / f"v{version}"
    result = build_patch(
        corpus,
        translations,
        version,
        build_dir,
        strict=True,
        catalog_path=CATALOG_PATH,
    )

    zip_path = DIST_DIR / f"WH40K-DOW2-chs-v{version}.zip"
    create_zip(build_dir, zip_path)
    digest = _sha256(zip_path)
    write_text_exact(
        DIST_DIR / f"{zip_path.name}.sha256",
        f"{digest}  {zip_path.name}\n",
    )

    return ReleaseResult(version=version, zip_path=zip_path, sha256=digest, build=result)
