"""Prepare a mod's game/ folder for translation editing."""
import os
import shutil
from pathlib import Path

from . import rpa
from ..config import load_settings
from .indexer import index_workspace
from .project import Project

SKIP_FILES = {"log.txt", "errors.txt", "traceback.txt", ".ds_store"}


class WorkspaceError(Exception):
    pass


def _skip_dir(relative):
    relative = relative.replace("\\", "/").strip("/")
    if relative in ("game/saves", "game/cache"):
        return True
    if relative.startswith(("game/saves/", "game/cache/")):
        return True
    parts = relative.split("/")
    return "__pycache__" in parts or ".git" in parts


def _skip_file(relative):
    return Path(relative).name.lower() in SKIP_FILES


def _copy_game(source_game, target_game, log):
    copied = 0
    for dirpath, dirnames, filenames in os.walk(source_game):
        current = Path(dirpath).relative_to(source_game)
        dirnames[:] = [
            name for name in dirnames
            if not _skip_dir((Path("game") / current / name).as_posix())]
        target_dir = target_game / current
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            relative = (current / name).as_posix()
            if _skip_file(relative):
                continue
            shutil.copy2(Path(dirpath) / name, target_dir / name)
            copied += 1
            if copied % 200 == 0:
                log("Copied %d files..." % copied)
    return copied


def _extract_rpas(game, log):
    archives = sorted(path for path in game.rglob("*.rpa")
                      if path.is_file())
    for archive in archives:
        log("Extracting %s..." % archive.relative_to(game).as_posix())
        try:
            names = rpa.extract_all(archive, archive.parent)
        except rpa.RPAError as exc:
            raise WorkspaceError(str(exc)) from exc
        log("Extracted %d files." % len(names))
        try:
            archive.unlink()
        except OSError as exc:
            raise WorkspaceError(
                "Could not remove %s after extraction: %s" %
                (archive.name, exc)) from exc
    return len(archives)


def _decompile_scripts(game, log, version="", settings=None):
    from .decompiler import DecompileError, decompile, decompile_legacy
    from .sdk import find_python27
    scripts = [path for path in game.rglob("*")
               if path.is_file() and
               path.suffix.lower() in (".rpyc", ".rpymc")]
    python27 = None
    if version == "6" and scripts:
        python27 = find_python27(version, settings or load_settings())
    for script in sorted(scripts):
        suffix = ".rpym" if script.suffix.lower() == ".rpymc" else ".rpy"
        if script.with_suffix(suffix).exists():
            continue
        log("Decompiling %s..." % script.relative_to(game).as_posix())
        try:
            if python27 is not None:
                decompile_legacy(script, python27, log)
            else:
                decompile(script)
        except DecompileError as exc:
            raise WorkspaceError(str(exc)) from exc
    return len(scripts)


def _snapshot(game, destination):
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    for script in game.rglob("*.rpy"):
        relative = script.relative_to(game)
        target = destination / "game" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script, target)
    return destination


def prepare_project(source_root, project_dir, version="", settings=None,
                    log=None):
    log = log or (lambda _message: None)
    source_root = Path(source_root)
    project_dir = Path(project_dir)
    game = project_dir / "workspace" / "game"
    if game.exists():
        shutil.rmtree(game)
    game.mkdir(parents=True)
    log("Copying mod game/...")
    _copy_game(source_root / "game", game, log)
    log("Extracting mod RPA archives...")
    _extract_rpas(game, log)
    log("Decompiling mod scripts...")
    _decompile_scripts(game, log, version, settings)
    snapshot = _snapshot(game, project_dir / "workspace" / "original")
    project = Project(project_dir)
    try:
        stats = index_workspace(project, project_dir / "workspace", snapshot)
    finally:
        project.close()
    log("Indexed %(files)d files and %(strings)d strings." % stats)
    return game, snapshot, stats
