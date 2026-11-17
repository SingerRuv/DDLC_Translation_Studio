"""Build a playable translated mod."""
import os
import shutil
import tempfile
from pathlib import Path

from ..config import MODS_ROOT
from .modinfo import ASSET_RPAS, validate_base
from .project import Project
from .rewrite import apply_translations, translated_files
from .sdk import compile_project, find_sdk
from .validate import validate_project

SKIP_FILES = {"log.txt", "errors.txt", "traceback.txt", ".ds_store"}
BASE_ASSETS = {"fonts.rpa", "images.rpa", "audio.rpa"}


class BuildError(Exception):
    pass


def _skip_dir(relative):
    relative = relative.replace("\\", "/").strip("/")
    return ("__pycache__" in relative.split("/") or
            ".git" in relative.split("/"))


def _copy_runtime(source, staging, log):
    copied = 0
    for dirpath, dirnames, filenames in os.walk(source):
        current = Path(dirpath).relative_to(source)
        if current == Path("."):
            dirnames[:] = [name for name in dirnames
                           if name not in ("game", "__pycache__", ".git")]
        else:
            dirnames[:] = [name for name in dirnames
                           if not _skip_dir((current / name).as_posix())]
        target_dir = staging / current
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            if Path(name).name.lower() in SKIP_FILES:
                continue
            relative = (current / name).as_posix()
            if _skip_dir(relative):
                continue
            shutil.copy2(Path(dirpath) / name, target_dir / name)
            copied += 1
            if copied % 200 == 0:
                log("Copied %d runtime files..." % copied)
    return copied


def _output_path(source):
    root = Path(MODS_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    name = Path(source).name + " - Translated"
    candidate = root / name
    number = 2
    while candidate.exists():
        candidate = root / ("%s (%d)" % (name, number))
        number += 1
    return candidate


def _remove_extra_archives(staging, log):
    game = staging / "game"
    keep = {(game / name).resolve() for name in BASE_ASSETS}
    removed = 0
    for archive in staging.rglob("*.rpa"):
        if archive.resolve() in keep:
            continue
        try:
            archive.unlink()
            removed += 1
        except OSError as exc:
            raise BuildError("Could not remove %s: %s" %
                             (archive.relative_to(staging), exc)) from exc
    if removed:
        log("Removed %d mod archive(s)." % removed)


def _copy_base_game_support(base, staging, log):
    source = Path(base) / "game" / "python-packages"
    target = staging / "game" / "python-packages"
    if not source.is_dir() or target.exists():
        return
    shutil.copytree(source, target)
    log("Copied base python-packages/.")


def _patch_overlay_checks(staging, log):
    changed = 0
    for script in (staging / "game").rglob("*.rpy"):
        try:
            text = script.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "if archive not in config.archives:" not in text:
            continue
        text = text.replace("if archive not in config.archives:",
                            "if False:  # base assets are present at runtime")
        script.write_text(text, encoding="utf-8")
        changed += 1
    if changed:
        log("Adjusted %d DDLC archive check(s) for the overlay build." %
            changed)


def _remove_untranslated_sources(staging, translated):
    removed = 0
    for script in list((staging / "game").rglob("*.rpy")):
        relative = script.relative_to(staging).as_posix()
        if relative not in translated:
            script.unlink()
            removed += 1
    return removed


def find_launcher(root):
    root = Path(root)
    try:
        files = sorted(root.iterdir())
    except OSError:
        return None
    for suffix in (".exe", ".sh", ".py"):
        candidates = [
            item for item in files
            if item.is_file() and item.suffix.lower() == suffix]
        if candidates:
            return min(candidates, key=lambda item:
                       (len(item.name), item.name.lower()))
    for item in files:
        if item.is_dir() and item.suffix.lower() == ".app":
            return item
    return None


def build_project(project_path, settings, log=None):
    log = log or (lambda _message: None)
    project = Project(project_path)
    try:
        source = project.get_meta("source")
        base = project.get_meta("base")
        source_kind = project.get_meta("source_kind", "runtime")
        runtime_source = project.get_meta("runtime_source") or source
        version = project.get_meta("renpy_version")
        if not source or not Path(source).is_dir():
            raise BuildError("The source project is not available.")
        if not runtime_source or not Path(runtime_source).is_dir():
            raise BuildError("The runtime source is not available.")
        if not base or not Path(base).is_dir():
            raise BuildError("The DDLC base is not available.")
        try:
            validate_base(base)
        except Exception as exc:
            raise BuildError(str(exc)) from exc
        sdk = find_sdk(version, settings)
        workspace_root = Path(project_path) / "workspace"
        source_root = Path(project_path) / "workspace" / "original"
        if not (workspace_root / "game").is_dir():
            raise BuildError("The workspace game folder is missing.")
        log("Applying translations...")
        result = apply_translations(project, workspace_root, source_root)
        if result["errors"]:
            detail = "; ".join("%s:%s: %s" % item
                               for item in result["errors"][:10])
            raise BuildError("Could not apply translations: %s" % detail)
        warnings = validate_project(project)
        translated = set(translated_files(project))
        output = _output_path(source)
        Path(MODS_ROOT).mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(
            prefix="DDLCTranslationStudio-build-", dir=str(MODS_ROOT)))
        try:
            log("Copying runtime...")
            _copy_runtime(Path(runtime_source), staging, log)
            log("Copying translated game...")
            shutil.copytree(workspace_root / "game", staging / "game")
            if source_kind == "overlay":
                _copy_base_game_support(base, staging, log)
            log("Copying DDLC base assets...")
            for relative in ASSET_RPAS:
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(base) / relative, target)
            _remove_extra_archives(staging, log)
            if source_kind == "overlay":
                _patch_overlay_checks(staging, log)
            log("Compiling with Ren'Py %s..." % version)
            compile_project(staging, sdk, log)
            removed = _remove_untranslated_sources(staging, translated)
            if removed:
                log("Removed %d unmodified source script(s)." % removed)
            if output.exists():
                raise BuildError("The output folder appeared during build.")
            staging.rename(output)
            log("Build ready: %s" % output)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {
            "path": output,
            "warnings": warnings,
            "launcher": find_launcher(output),
            "sdk": sdk,
        }
    finally:
        project.close()
