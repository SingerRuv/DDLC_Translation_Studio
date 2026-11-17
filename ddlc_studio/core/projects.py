"""Project creation and lookup."""
import shutil
from pathlib import Path

from ..config import PROJECTS_ROOT
from .modinfo import (ModInfoError, detect_renpy_version, validate_base,
                      validate_source)
from .project import Project


class ProjectError(Exception):
    pass


def _safe_name(value):
    value = "".join("_" if char in '<>:"/\\|?*' or ord(char) < 32 else char
                    for char in str(value))
    return value.strip(" .") or "mod"


def project_path_for(source_root, projects_root=None):
    root = Path(projects_root or PROJECTS_ROOT)
    return root / _safe_name(Path(source_root).name)


def _existing(project_dir):
    return (Path(project_dir) / "project.sqlite3").is_file()


def summary_from_path(project_dir):
    path = Path(project_dir)
    if not _existing(path):
        raise ProjectError("Not a translation project: %s" % path)
    project = Project(path)
    try:
        source = project.get_meta("source")
        base = project.get_meta("base")
        workspace = project.get_meta("workspace")
        version = project.get_meta("renpy_version")
        kind = project.get_meta("source_kind", "runtime")
        files = len(project.files())
        strings = len(project.strings())
    finally:
        project.close()
    return {
        "path": str(path),
        "name": path.name,
        "source": source,
        "base": base,
        "workspace": workspace,
        "version": version,
        "kind": kind,
        "files": files,
        "strings": strings,
    }


def create_project(base_path, source_path, project_dir=None, settings=None,
                   log=None):
    log = log or (lambda _message: None)
    from .workspace import prepare_project
    try:
        base = validate_base(base_path)
        source, source_version, kind = validate_source(source_path)
    except ModInfoError as exc:
        raise ProjectError(str(exc)) from exc
    base_version = detect_renpy_version(base)
    runtime_source = base if kind == "overlay" else source
    version = base_version if kind == "overlay" else source_version
    project_dir = Path(project_dir or project_path_for(source))
    if project_dir.exists():
        if _existing(project_dir):
            log("Opening existing project %s" % project_dir)
            return summary_from_path(project_dir)
        try:
            if any(project_dir.iterdir()):
                raise ProjectError(
                    "The project folder exists and is not a translation "
                    "project: %s" % project_dir)
        except OSError as exc:
            raise ProjectError(str(exc)) from exc
    project_dir.mkdir(parents=True, exist_ok=True)
    project = Project(project_dir)
    try:
        project.set_meta("base", base)
        project.set_meta("source", source)
        project.set_meta("source_kind", kind)
        project.set_meta("runtime_source", runtime_source)
        project.set_meta("renpy_version", version)
        project.set_meta("workspace", project_dir / "workspace" / "game")
        game, _snapshot, stats = prepare_project(
            source, project_dir, version, settings, log=log)
        project.set_meta("workspace", game)
        project.set_meta("files", stats["files"])
        project.set_meta("strings", stats["strings"])
    except Exception:
        project.close()
        shutil.rmtree(project_dir, ignore_errors=True)
        raise
    project.close()
    return {
        "path": str(project_dir),
        "name": project_dir.name,
        "source": str(source),
        "base": str(base),
        "workspace": str(project_dir / "workspace" / "game"),
        "version": version,
        "kind": kind,
        "files": stats["files"],
        "strings": stats["strings"],
    }

