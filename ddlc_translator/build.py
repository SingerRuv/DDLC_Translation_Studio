"""Build a translated copy of a mod."""
from pathlib import Path

from .rewrite import apply_translations
from .workspace import copy_mod


class BuildError(Exception):
    pass


def _translated_files(project):
    rows = [row for row in project.strings() if row["translation"].strip()]
    return sorted({row["relative_path"] for row in rows})


def build_translated(project, workspace, output, tools=None, log=print):
    source = project.get_meta("source")
    if not source or not Path(source).exists():
        raise BuildError("The original mod path is not available.")
    files = _translated_files(project)
    if not files:
        raise BuildError("There are no translated strings to build.")
    if tools is None:
        raise BuildError("No tool configuration provided.")
    log("Applying latest translations...")
    result = apply_translations(project, workspace)
    if result["errors"]:
        detail = "; ".join("%s:%s: %s" % item for item in result["errors"])
        raise BuildError("Could not apply translations: %s" % detail)
    log("Compiling translated scripts...")
    tools.compile_project(workspace)
    generated = []
    for relative in files:
        source_script = Path(workspace) / relative
        compiled = source_script.with_suffix(".rpyc")
        if not compiled.is_file():
            raise BuildError("Compiled script not found: %s" % relative)
        generated.append((relative, compiled))
    log("Copying original mod...")
    destination = copy_mod(source, output)
    for relative, compiled in generated:
        target = destination / Path(relative).with_suffix(".rpyc")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(compiled.read_bytes())
    log("Translated build ready: %s" % destination)
    return destination
