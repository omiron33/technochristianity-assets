#!/usr/bin/env python3
"""Prepare a new immutable runtime-asset release from generated Dubrovitsy files.

Example:
    python3 scripts/prepare-dubrovitsy-release.py \
      --public-root /Volumes/Code/Technochristian-dubrovitsy-recovery/public \
      --release 2026-09-22-dubrovitsy-final

The published 2026-09-22 release is read only. This script copies it into a
temporary directory, substitutes the generated Dubrovitsy model package, then
atomically installs a *new* release directory after every check passes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


MODEL = "sign-of-the-theotokos-dubrovitsy"
MODEL_REL = Path("church") / MODEL
BASELINE_NAME = "2026-09-22"
MAX_FILE_BYTES = 25_000_000  # Strictly less than this value.
REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "releases" / BASELINE_NAME


class ReleaseError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"Cannot read JSON {path}: {exc}") from exc
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def safe_relative(name: str) -> Path:
    require(isinstance(name, str) and bool(name), f"Invalid relative path: {name!r}")
    parts = urlsplit(name)
    require(not (parts.scheme or parts.netloc or parts.query or parts.fragment),
            f"External or qualified URI is not packaged: {name}")
    decoded = unquote(parts.path)
    posix = PurePosixPath(decoded)
    require(not (posix.is_absolute() or "\\" in decoded or any(p in ("", ".", "..") for p in decoded.split("/"))),
            f"Unsafe package path: {name}")
    return Path(*posix.parts)


def safe_file(root: Path, relative: str) -> Path:
    path = root / safe_relative(relative)
    require(path.is_file(), f"Missing package file: {path}")
    require(not path.is_symlink(), f"Symlink is not allowed: {path}")
    require(path.resolve().is_relative_to(root.resolve()), f"Package file escapes root: {path}")
    return path


def checked_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*"):
        require(not path.is_symlink(), f"Symlink is not allowed: {path}")
        if path.is_file():
            require(path.stat().st_size < MAX_FILE_BYTES,
                    f"File is at least {MAX_FILE_BYTES:,} bytes: {path}")
            result.append(path)
    return sorted(result)


def digest(path: Path) -> dict:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return {"byteLength": size, "sha256": h.hexdigest()}


def verify_file_map(root: Path, entries: dict, *, exact: bool) -> None:
    require(isinstance(entries, dict), f"Invalid file map under {root}")
    for name, expected in entries.items():
        path = safe_file(root, name)
        require(isinstance(expected, dict) and digest(path) == expected,
                f"Package manifest hash or size mismatch: {path}")
    if exact:
        actual = {p.relative_to(root).as_posix() for p in checked_files(root)} - {"manifest.json"}
        require(actual == set(entries),
                f"Release manifest differs from files on disk: missing={sorted(set(entries)-actual)}, "
                f"unlisted={sorted(actual-set(entries))}")


def gltf_uris(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "uri" and isinstance(child, str):
                yield child
            else:
                yield from gltf_uris(child)
    elif isinstance(value, list):
        for child in value:
            yield from gltf_uris(child)


def verify_gltf(root: Path, package: dict) -> dict:
    gltf_name = package.get("gltf")
    gltf_path = safe_file(root, gltf_name)
    gltf = read_json(gltf_path)
    require(gltf.get("asset", {}).get("version", "").startswith("2."),
            f"Expected glTF 2 model: {gltf_path}")
    files = package.get("files")
    require(isinstance(files, dict) and gltf_name in files,
            f"Package manifest omits its glTF: {gltf_path}")
    for uri in gltf_uris(gltf):
        if uri.startswith("data:"):
            continue
        relative = safe_relative(uri).as_posix()
        require(relative in files, f"glTF dependency is absent from package manifest: {uri}")
        safe_file(root, relative)
    for buffer in gltf.get("buffers", []):
        uri = buffer.get("uri")
        if uri and not uri.startswith("data:"):
            require(safe_file(root, uri).stat().st_size >= buffer["byteLength"],
                    f"glTF buffer is shorter than its declared length: {uri}")
    return gltf


def verify_buffer_views(root: Path, package: dict, gltf: dict) -> None:
    views = package.get("bufferViews", [])
    require(isinstance(views, list), "Invalid package bufferViews")
    packaged_views = gltf.get("bufferViews", [])
    buffers = gltf.get("buffers", [])
    for entry in views:
        uri = entry["uri"]
        offset = entry["byteOffset"]
        length = entry["byteLength"]
        require(isinstance(offset, int) and offset >= 0 and isinstance(length, int) and length >= 0,
                f"Invalid bufferView span for {uri}")
        path = safe_file(root, uri)
        require(offset + length <= path.stat().st_size,
                f"bufferView exceeds its file: {path}")
        with path.open("rb") as source:
            source.seek(offset)
            actual_hash = hashlib.sha256(source.read(length)).hexdigest()
        require(actual_hash == entry["sha256"],
                f"bufferView hash mismatch: {path} at byte {offset}")
        index = entry.get("packagedIndex")
        if index is not None:
            require(isinstance(index, int) and 0 <= index < len(packaged_views),
                    f"Invalid packaged bufferView index: {index}")
            view = packaged_views[index]
            require(view.get("byteOffset", 0) == offset and view["byteLength"] == length,
                    f"glTF/package bufferView span mismatch: {index}")
            require(buffers[view["buffer"]].get("uri") == uri,
                    f"glTF/package bufferView URI mismatch: {index}")


def verify_package(root: Path, model: str) -> dict:
    manifest = read_json(root / f"{model}-package-manifest.json")
    require(manifest.get("model") == model, f"Wrong model package at {root}")
    require(manifest.get("maxFileBytes") == MAX_FILE_BYTES,
            f"Unexpected package file limit at {root}")
    verify_file_map(root, manifest.get("files"), exact=False)
    gltf = verify_gltf(root, manifest)
    verify_buffer_views(root, manifest, gltf)
    validation = manifest.get("validation", {})
    require(validation.get("documentRoundTripEqual") is True and
            validation.get("compressedBytesPreserved") is True and
            validation.get("bufferViewsCompared") == len(manifest.get("bufferViews", [])) and
            validation.get("imagesCompared") == len(gltf.get("images", [])),
            f"Generated package validation is incomplete: {root}")
    return manifest


def verify_release(root: Path) -> dict:
    release = read_json(root / "manifest.json")
    require(release.get("formatVersion") == 1, "Unsupported release manifest")
    models = release.get("models")
    require(isinstance(models, list) and models, "Release has no models")
    verify_file_map(root, release.get("files"), exact=True)
    for model_path in models:
        gltf_path = safe_file(root, model_path)
        verify_package(gltf_path.parent, gltf_path.stem)
    return release


def generated_files(package: dict) -> set[str]:
    names = set(package["files"])
    require(package["gltf"] in names, "Generated package omits its glTF")
    return names | {f"{MODEL}-package-manifest.json"}


def replace_model(stage: Path, authoring: Path) -> None:
    source = authoring / MODEL_REL
    destination = stage / MODEL_REL
    require(source.is_dir() and not source.is_symlink(), f"Missing authoring model: {source}")
    require(destination.is_dir(), f"Baseline lacks Dubrovitsy model: {destination}")
    old = verify_package(destination, MODEL)
    new = verify_package(source, MODEL)
    for name in generated_files(old):
        safe_file(destination, name).unlink()
    for name in generated_files(new):
        src = safe_file(source, name)
        dst = destination / safe_relative(name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Keep the published LICENSE and photos. Carry forward authoring credits and
    # provenance when present so the generated textures retain their attribution.
    require((destination / "LICENSE.md").is_file(), "Baseline Dubrovitsy LICENSE missing")
    for name in ("credits.json", "photographic-provenance.json",
                 "textures/provenance.json", "textures/albedo-fields-provenance.json"):
        src = safe_file(source, name)
        dst = destination / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for path in source.rglob("*provenance*.json"):
        relative = path.relative_to(source).as_posix()
        if relative not in ("photographic-provenance.json", "textures/provenance.json",
                            "textures/albedo-fields-provenance.json"):
            src = safe_file(source, relative)
            dst = destination / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    authoring_license = source / "LICENSE.md"
    if authoring_license.exists():
        require(authoring_license.read_bytes() == (destination / "LICENSE.md").read_bytes(),
                "Authoring LICENSE differs from published LICENSE; review attribution before release")


def write_manifest(root: Path, baseline: dict, release_name: str) -> None:
    release = copy.deepcopy(baseline)
    release["release"] = release_name
    release["files"] = {
        path.relative_to(root).as_posix(): digest(path)
        for path in checked_files(root)
        if path.name != "manifest.json" or path.parent != root
    }
    (root / "manifest.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-root", type=Path, required=True,
                        help="Authoring checkout's public/ directory with generated Dubrovitsy files")
    parser.add_argument("--release", required=True, help="Unique new release directory name")
    parser.add_argument("--releases-root", type=Path, default=REPO / "releases",
                        help="Output parent; default is this repository's releases/ (use /tmp for rehearsal)")
    args = parser.parse_args()
    name = args.release
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)) and name != BASELINE_NAME,
            "Release name must be a safe, new single directory name")
    authoring = args.public_root.resolve(strict=True)
    require(authoring.is_dir(), f"Authoring public root is not a directory: {authoring}")
    releases_root = args.releases_root.resolve()
    require(not releases_root.is_relative_to(BASELINE), "Output root cannot be inside published baseline")
    require(not releases_root.is_relative_to(authoring), "Output root cannot be inside authoring public/")
    releases_root.mkdir(parents=True, exist_ok=True)
    target = releases_root / name
    require(not target.exists() and not target.is_symlink(), f"Refusing existing release: {target}")
    require(BASELINE.is_dir(), f"Missing immutable baseline release: {BASELINE}")
    baseline = verify_release(BASELINE)

    with tempfile.TemporaryDirectory(prefix=f".{name}-staging-", dir=releases_root) as temporary:
        stage = Path(temporary) / "release"
        shutil.copytree(BASELINE, stage, symlinks=False)
        replace_model(stage, authoring)
        write_manifest(stage, baseline, name)
        prepared = verify_release(stage)
        require(prepared["release"] == name, "Prepared release name mismatch")
        for path, expected in baseline["files"].items():
            if not path.startswith(MODEL_REL.as_posix() + "/"):
                require(prepared["files"].get(path) == expected,
                        f"Non-Dubrovitsy file changed: {path}")
        # mkdir reserves the final name exclusively. Replacing this empty
        # directory with the verified staged tree is atomic on the same volume.
        try:
            target.mkdir()
        except FileExistsError as exc:
            raise ReleaseError(f"Refusing existing release: {target}") from exc
        try:
            os.replace(stage, target)
        except Exception:
            target.rmdir()
            raise
    print(f"Prepared {target} ({len(prepared['files'])} files; all hashes, glTF dependencies, "
          f"buffer views, and {MAX_FILE_BYTES:,}-byte limits verified)")


if __name__ == "__main__":
    try:
        main()
    except (ReleaseError, OSError, KeyError, TypeError, IndexError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
