"""DDLC base and Ren'Py source project discovery."""
import os
import re
from pathlib import Path

from . import rpa

LAUNCHER_SUFFIXES = (".exe", ".sh", ".py", ".app")
BASE_RPAS = ("game/scripts.rpa", "game/images.rpa", "game/audio.rpa",
             "game/fonts.rpa")
ASSET_RPAS = ("game/fonts.rpa", "game/images.rpa", "game/audio.rpa")


class ModInfoError(Exception):
    pass


def _rpa_ok(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(8).startswith(b"RPA-3.0")
    except OSError:
        return False


def _has_launcher(path):
    try:
        for item in path.iterdir():
            if item.suffix.lower() in LAUNCHER_SUFFIXES:
                return True
            if item.is_dir() and item.suffix.lower() == ".app":
                return True
    except OSError:
        return False
    return False


def _version_from_text(text):
    match = re.search(r"version_tuple\s*=\s*\(\s*(\d+)", text)
    if match:
        return match.group(1)
    match = re.search(r"version\s*=\s*[\"']Ren'Py\s+(\d+)", text)
    return match.group(1) if match else ""


def detect_renpy_version(root):
    root = Path(root)
    init_file = root / "renpy" / "__init__.py"
    try:
        version = _version_from_text(
            init_file.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        version = ""
    if version:
        return version
    lib = root / "lib"
    try:
        names = [item.name for item in lib.iterdir() if item.is_dir()]
    except OSError:
        names = []
    if any(name.startswith("py3-") for name in names):
        return "8"
    if any(name.startswith("py2-") for name in names):
        return "7"
    if any(name.startswith(("python2", "pythonlib2")) for name in names):
        return "6"
    return ""


def validate_base(path):
    base = Path(path)
    if not base.is_dir():
        raise ModInfoError("The DDLC base folder does not exist.")
    launchers = ("DDLC.exe", "DDLC.sh", "DDLC.py", "DDLC.app")
    if not any((base / name).exists() for name in launchers):
        raise ModInfoError("The base does not look like DDLC.")
    for name in ("game", "lib", "renpy"):
        if not (base / name).is_dir():
            raise ModInfoError("The base is missing %s/." % name)
    if not (base / "game" / "python-packages").is_dir():
        raise ModInfoError("The base is missing game/python-packages/.")
    for relative in BASE_RPAS:
        if not _rpa_ok(base / relative):
            raise ModInfoError("The base is missing a valid %s." % relative)
    return base.resolve()


def _is_source_root(path):
    path = Path(path)
    return ((path / "game").is_dir() and (path / "lib").is_dir() and
            (path / "renpy").is_dir() and _has_launcher(path))


def _is_overlay_root(path):
    path = Path(path)
    game = path / "game"
    return (game.is_dir() and (game / "scripts.rpa").is_file() and
            (game / "mod_assets.rpa").is_file() and
            rpa.has_scripts(game / "scripts.rpa"))


def find_source_root(path):
    path = Path(path)
    if not path.exists():
        raise ModInfoError("The source project path does not exist.")
    candidates = [path]
    if path.is_dir():
        try:
            candidates.extend(item for item in path.iterdir()
                              if item.is_dir())
        except OSError:
            pass
    for candidate in candidates:
        if _is_source_root(candidate):
            return candidate.resolve(), "runtime"
        if _is_overlay_root(candidate):
            return candidate.resolve(), "overlay"
    for root, dirs, _files in os.walk(path):
        dirs[:] = [name for name in dirs if name not in (".git", "__MACOSX")]
        candidate = Path(root)
        if _is_source_root(candidate):
            return candidate.resolve(), "runtime"
        if _is_overlay_root(candidate):
            return candidate.resolve(), "overlay"
    raise ModInfoError("No Ren'Py runtime or DDLC overlay project found.")


def _has_scripts(game):
    try:
        for suffix in (".rpy", ".rpyc", ".rpym", ".rpymc"):
            if any(game.rglob("*" + suffix)):
                return True
        for archive in game.rglob("*.rpa"):
            if rpa.has_scripts(archive):
                return True
    except OSError:
        return False
    return False


def validate_source(path):
    root, kind = find_source_root(path)
    game = root / "game"
    if not _has_scripts(game):
        raise ModInfoError(
            "The source project has no .rpy/.rpyc scripts or script RPA.")
    if kind == "runtime":
        version = detect_renpy_version(root)
        if version not in ("6", "7", "8"):
            raise ModInfoError(
                "Could not detect a supported Ren'Py version in the source.")
    else:
        version = ""
    return root, version, kind

