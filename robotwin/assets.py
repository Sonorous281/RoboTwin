"""Download, validate, and resolve the external RoboTwin asset snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml
from huggingface_hub import snapshot_download

ASSET_REPOSITORY = "TianxingChen/RoboTwin2.0"
ASSET_REVISION = "c15cc97be71e35244b6605d2d84c187f8565cc4d"
ASSET_ARCHIVES = (
    "background_texture.zip",
    "embodiments.zip",
    "objects.zip",
)
MANIFEST_NAME = ".robotwin-assets.json"
REQUIRED_ASSET_DIRECTORIES = (
    "assets/background_texture",
    "assets/embodiments/aloha-agilex",
    "assets/objects",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive_path: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(
                    f"unsafe RoboTwin asset archive member: {member.filename}"
                )
        archive.extractall(destination)


def validate_root(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Validate an asset root and return its stable runtime identity."""
    root = Path(path).expanduser().resolve()
    missing = [
        str(root / value)
        for value in REQUIRED_ASSET_DIRECTORIES
        if not (root / value).is_dir()
    ]
    if missing:
        raise ValueError(
            "RoboTwin asset snapshot is incomplete; missing directories: "
            f"{missing}"
        )

    manifest_path = root / MANIFEST_NAME
    manifest: dict[str, Any] | None = None
    if manifest_path.is_file():
        with manifest_path.open("r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        if not isinstance(loaded, dict):
            raise ValueError(f"invalid RoboTwin asset manifest: {manifest_path}")
        manifest = loaded
        revision = manifest.get("revision")
        if revision != ASSET_REVISION:
            raise ValueError(
                "RoboTwin asset revision mismatch: "
                f"expected {ASSET_REVISION}, got {revision!r}"
            )

    return {
        "root": str(root),
        "repository": ASSET_REPOSITORY,
        "revision": manifest.get("revision") if manifest else None,
        "managed": manifest is not None,
        "manifest": str(manifest_path) if manifest else None,
    }


def _expand_asset_path(value: Any, assets_root: Path) -> Any:
    if isinstance(value, str):
        return value.replace("${ASSETS_PATH}", str(assets_root))
    if isinstance(value, dict):
        return {
            key: _expand_asset_path(item, assets_root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_expand_asset_path(item, assets_root) for item in value]
    return value


def load_curobo_config(
    embodiment_root: str | os.PathLike[str], arm: str
) -> dict[str, Any]:
    """Load a relocatable cuRobo config and expand its paths in memory."""
    if arm not in {"left", "right"}:
        raise ValueError("arm must be 'left' or 'right'")
    embodiment = Path(embodiment_root).expanduser().resolve()
    runtime_root = embodiment.parents[2]
    config_path = embodiment / f"curobo_{arm}_tmp.yml"
    if not config_path.is_file():
        raise ValueError(
            "RoboTwin relocatable cuRobo config not found: "
            f"{config_path}. Re-download the pinned asset snapshot."
        )
    with config_path.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict) or "robot_cfg" not in config:
        raise ValueError(f"invalid RoboTwin cuRobo config: {config_path}")
    return _expand_asset_path(config, runtime_root)


def download_assets(output: str | os.PathLike[str]) -> dict[str, Any]:
    """Download the pinned asset archives into a relocatable runtime root."""
    root = Path(output).expanduser().resolve()
    try:
        return validate_root(root)
    except ValueError:
        if root.exists() and any(root.iterdir()):
            raise ValueError(
                "RoboTwin asset output exists but is not a complete managed "
                f"snapshot: {root}. Choose an empty output directory."
            ) from None

    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{root.name}-",
        dir=root.parent,
    ) as staging_dir:
        staging_root = Path(staging_dir)
        assets_dir = staging_root / "assets"
        assets_dir.mkdir()
        archive_hashes: dict[str, str] = {}
        download_dir = staging_root / "downloads"
        snapshot_root = Path(
            snapshot_download(
                repo_id=ASSET_REPOSITORY,
                repo_type="dataset",
                revision=ASSET_REVISION,
                allow_patterns=list(ASSET_ARCHIVES),
                local_dir=download_dir,
            )
        )
        for name in ASSET_ARCHIVES:
            archive = snapshot_root / name
            if not archive.is_file():
                raise RuntimeError(f"RoboTwin asset archive is missing: {archive}")
            archive_hashes[name] = _sha256(archive)
            _safe_extract(archive, assets_dir)
        if download_dir.exists():
            shutil.rmtree(download_dir)

        manifest = {
            "repository": ASSET_REPOSITORY,
            "revision": ASSET_REVISION,
            "archives": archive_hashes,
        }
        (staging_root / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        validate_root(staging_root)
        if root.exists():
            root.rmdir()
        os.replace(staging_root, root)

    return validate_root(root)


def main() -> None:
    """CLI entry point for downloading the pinned RoboTwin assets."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(download_assets(args.output), indent=2, sort_keys=True))


__all__ = [
    "ASSET_REPOSITORY",
    "ASSET_REVISION",
    "download_assets",
    "load_curobo_config",
    "validate_root",
]
