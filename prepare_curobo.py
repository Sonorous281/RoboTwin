"""Prepare the pinned cuRobo v0.7.8 source for a release wheel."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

CUROBO_REVISION = "d64c4b005459db10c5dd867d8b30a87d5bda9bdb"
CUROBO_REPOSITORY = "https://github.com/NVlabs/curobo.git"


def _run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def _fetch_repository(destination: Path) -> Path:
    _run("git", "init", str(destination))
    _run("git", "remote", "add", "origin", CUROBO_REPOSITORY, cwd=destination)
    _run("git", "fetch", "--depth", "1", "origin", CUROBO_REVISION, cwd=destination)
    return destination


def _archive_repository(repository: Path, destination: Path) -> None:
    _run("git", "cat-file", "-e", f"{CUROBO_REVISION}^{{commit}}", cwd=repository)
    _run(
        "git",
        "archive",
        "--format=tar.gz",
        f"--output={destination}",
        CUROBO_REVISION,
        cwd=repository,
    )


def _extract_archive(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        root = destination.resolve()
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe cuRobo archive member: {member.name}")
        tar.extractall(destination)


def main() -> None:
    """Download, verify, and unpack the pinned cuRobo source tree."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path)
    args = parser.parse_args()

    package_root = Path(__file__).resolve().parent
    vendor_root = package_root / "vendor" / "curobo"
    if vendor_root.exists():
        shutil.rmtree(vendor_root)

    with tempfile.TemporaryDirectory(prefix="rlinf-curobo-") as temp_dir:
        temp_root = Path(temp_dir)
        repository = (
            args.source_repo.expanduser().resolve()
            if args.source_repo is not None
            else _fetch_repository(temp_root / "repository")
        )
        archive = temp_root / "curobo.tar.gz"
        _archive_repository(repository, archive)
        extract_root = temp_root / "source"
        extract_root.mkdir()
        _extract_archive(archive, extract_root)
        vendor_root.mkdir(parents=True)
        shutil.copy2(extract_root / "LICENSE", vendor_root / "LICENSE")
        shutil.copy2(
            extract_root / "LICENSE_ASSETS",
            vendor_root / "LICENSE_ASSETS",
        )
        shutil.copytree(
            extract_root / "src" / "curobo",
            vendor_root / "src" / "curobo",
        )
        package_root = vendor_root / "src" / "curobo"
        for license_name in ("LICENSE", "LICENSE_ASSETS"):
            shutil.copy2(vendor_root / license_name, package_root / license_name)


if __name__ == "__main__":
    main()
