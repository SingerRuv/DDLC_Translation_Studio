"""Ren'Py SDK discovery and compilation."""
import subprocess
from pathlib import Path

from .modinfo import detect_renpy_version

CREATE_NO_WINDOW = 0x08000000
TAIL_LINES = 80


class SDKError(Exception):
    pass


def _launcher(root):
    root = Path(root)
    for name in ("renpy.exe", "renpy.py", "renpy.sh"):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _version(root):
    version = detect_renpy_version(root)
    if version in ("6", "7", "8"):
        return version
    name = Path(root).name.lower()
    for marker in ("renpy-6", "renpy-7", "renpy-8", "renpy6", "renpy7",
                   "renpy8"):
        if marker in name:
            return marker[-1]
    return ""


def find_sdk(version, settings):
    key = "renpy%s" % version
    configured = settings.get(key, "").strip()
    if configured:
        path = Path(configured)
        if path.is_file():
            return path
        launcher = _launcher(path)
        if launcher:
            return launcher
    roots = [Path.home() / "Desktop", Path.home() / "Downloads",
             Path.home(), Path.home() / "AppData" / "Local" / "Programs"]
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        candidates = []
        for child in children:
            if not child.is_dir():
                continue
            candidates.append(child)
            if "sdk" in child.name.lower():
                try:
                    candidates.extend(item for item in child.iterdir()
                                      if item.is_dir())
                except OSError:
                    pass
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            launcher = _launcher(candidate)
            if launcher and _version(candidate) == version:
                return launcher
    raise SDKError("No Ren'Py %s SDK found. Configure it in Settings." %
                   version)


def find_python27(version, settings):
    sdk = find_sdk(version, settings)
    root = Path(sdk).parent
    candidates = [
        root / "lib" / "windows-i686" / "python.exe",
        root / "lib" / "py2-windows-i686" / "python.exe",
        root / "lib" / "py2-windows-x86_64" / "python.exe",
        root / "lib" / "python2.7" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SDKError("Could not find Python 2.7 in the Ren'Py %s SDK." %
                   version)


def compile_project(project, sdk, log=None):
    log = log or (lambda _message: None)
    command = [str(sdk), str(project), "compile"]
    log("Running: %s" % " ".join(command))
    try:
        process = subprocess.run(
            command, cwd=str(project), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", creationflags=CREATE_NO_WINDOW)
    except OSError as exc:
        raise SDKError("Could not run the Ren'Py SDK: %s" % exc) from exc
    tail = "\n".join(process.stdout.splitlines()[-TAIL_LINES:])
    if tail:
        log(tail)
    lower = tail.lower()
    fatal = ("expected statement", "syntaxerror", "atl statement contains",
             "ddlc archive files not found", "exception(")
    if process.returncode or any(marker in lower for marker in fatal):
        raise SDKError("Ren'Py compilation failed (exit %s).\n%s" %
                       (process.returncode, tail))
    return tail
