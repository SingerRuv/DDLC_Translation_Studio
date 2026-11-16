"""Workspace preparation: copy, extract, and decompile."""
import shutil
from pathlib import Path

from .modinfo import find_mod_root
from .tools import ToolConfig


class WorkspaceError(Exception):
    pass


def copy_mod(mod_path, destination):
    root = find_mod_root(mod_path)
    destination = Path(destination)
    if destination == root or root in destination.parents:
        raise WorkspaceError("Workspace cannot be inside the original mod.")
    if destination.exists():
        if any(destination.iterdir()):
            raise WorkspaceError("Workspace destination is not empty.")
        destination.rmdir()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root, destination)
    return destination


def copy_scripts(mod_path, destination):
    root = find_mod_root(mod_path)
    destination = Path(destination)
    if destination == root or root in destination.parents:
        raise WorkspaceError("Workspace cannot be inside the original mod.")
    if destination.exists():
        if any(destination.iterdir()):
            raise WorkspaceError("Workspace destination is not empty.")
        destination.rmdir()
    source_game = root / "game"
    target_game = destination / "game"
    target_game.mkdir(parents=True, exist_ok=True)
    found = False
    for item in source_game.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in (".rpy", ".rpyc"):
            continue
        relative = item.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        found = True
    scripts_rpa = source_game / "scripts.rpa"
    if scripts_rpa.is_file():
        shutil.copy2(scripts_rpa, target_game / scripts_rpa.name)
        found = True
    if not found:
        raise WorkspaceError("No scripts found in the selected mod.")
    return destination


def game_dir(workspace):
    return Path(workspace) / "game"


def archives(workspace):
    return sorted(game_dir(workspace).glob("*.rpa"))


def scripts(workspace):
    return sorted(game_dir(workspace).rglob("*.rpyc"))


def snapshot_dir(project_dir):
    return Path(project_dir) / "workspace" / "original"


def _copy_scripts(workspace, destination):
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    for script in game_dir(workspace).rglob("*.rpy"):
        relative = script.relative_to(workspace)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script, target)


def prepare_workspace(mod_path, project_dir, tools=None, log=print):
    tools = tools or ToolConfig()
    tools.validate()
    workspace = Path(project_dir) / "workspace" / "mod"
    copy_scripts(mod_path, workspace)
    log("Copied scripts to workspace.")
    for archive in archives(workspace):
        log("Extracting %s..." % archive.name)
        tools.extract_rpa(archive, game_dir(workspace), cwd=archive.parent)
    for script in scripts(workspace):
        if script.with_suffix(".rpy").exists():
            log("Skipping decompiled source: %s" % script.name)
            continue
        log("Decompiling %s..." % script.name)
        tools.decompile_rpyc(script, cwd=script.parent)
    _copy_scripts(workspace, snapshot_dir(project_dir))
    return workspace
