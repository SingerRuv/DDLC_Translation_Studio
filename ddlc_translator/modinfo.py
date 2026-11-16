"""Ren'Py mod discovery and version detection."""
import re
from pathlib import Path

LAUNCHER_SUFFIXES = (".exe", ".sh", ".py", ".app")


class ModInfoError(Exception):
    pass


def _has_launcher(path):
    try:
        for item in path.iterdir():
            if item.suffix.lower() in LAUNCHER_SUFFIXES:
                return True
    except OSError:
        return False
    return False


def _is_mod_root(path):
    path = Path(path)
    if not (path / "game").is_dir():
        return False
    return ((path / "renpy").is_dir() or (path / "lib").is_dir() or
            _has_launcher(path))


def find_mod_root(path):
    path = Path(path)
    if not path.exists():
        raise ModInfoError("The selected path does not exist.")
    candidates = [path]
    if path.is_dir():
        try:
            candidates.extend(child for child in path.iterdir()
                              if child.is_dir())
        except OSError:
            pass
    for candidate in candidates:
        if _is_mod_root(candidate):
            return candidate.resolve()
    raise ModInfoError("No Ren'Py/DDLC mod root found.")


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

