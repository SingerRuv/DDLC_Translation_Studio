"""Command-line entry point for the translation workspace."""
import argparse
import csv
import sys
from pathlib import Path

from ddlc_translator.config import APP, load_settings
from ddlc_translator.build import BuildError, build_translated
from ddlc_translator.indexer import index_workspace
from ddlc_translator.modinfo import (ModInfoError, detect_renpy_version,
                                      find_mod_root)
from ddlc_translator.project import Project
from ddlc_translator.rewrite import apply_translations
from ddlc_translator.tools import ToolConfig, ToolError
from ddlc_translator.validate import validate as validate_text
from ddlc_translator.validate import validate_project
from ddlc_translator.workspace import (WorkspaceError, game_dir,
                                       prepare_workspace, snapshot_dir)




def _override_tools(settings, rpa_tool=None, rpyc_tool=None):
    settings = dict(settings)
    if rpa_tool:
        settings["rpa_extractor"] = rpa_tool
    if rpyc_tool:
        settings["rpyc_decompiler"] = rpyc_tool
    return settings


def command_detect(args):
    root = find_mod_root(args.mod)
    print("Root: %s" % root)
    print("Ren'Py: %s" % (detect_renpy_version(root) or "unknown"))
    print("Game: %s" % (root / "game"))
    return 0


def command_tools(args):
    settings = load_settings()
    config = ToolConfig(settings)
    try:
        config.validate()
    except ToolError as exc:
        print(exc, file=sys.stderr)
        return 1
    print("RPA extractor: %s" % settings.get("rpa_extractor"))
    print("RPYC decompiler: %s" % settings.get("rpyc_decompiler"))
    return 0


def command_prepare(args):
    settings = _override_tools(load_settings(), args.rpa_tool,
                              args.rpyc_tool)
    tools = ToolConfig(settings)
    project = Project(args.project)
    try:
        project.set_meta("source", args.mod)
        project.set_meta("app", APP)
        root = find_mod_root(args.mod)
        project.set_meta("mod_root", root)
        project.set_meta("renpy_version", detect_renpy_version(root))
        workspace = prepare_workspace(
            args.mod, args.project, tools=tools,
            log=lambda message: print(message, flush=True))
        project.set_meta("workspace", workspace)
        project.set_meta("snapshot", snapshot_dir(args.project))
        game = game_dir(workspace)
        for script in sorted(game.rglob("*.rpy")):
            project.add_file(script.relative_to(workspace), kind="script")
        print("Workspace ready: %s" % workspace)
        return 0
    except (ModInfoError, WorkspaceError, ToolError, OSError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        project.close()


def command_index(args):
    project = Project(args.project)
    try:
        workspace = project.get_meta("workspace")
        if not workspace:
            print("Project has no workspace.", file=sys.stderr)
            return 1
        source = project.get_meta("snapshot") or workspace
        stats = index_workspace(project, workspace, source)
        print("Indexed %(files)d files and %(strings)d strings." % stats)
        return 0
    finally:
        project.close()


def command_apply(args):
    project = Project(args.project)
    try:
        workspace = project.get_meta("workspace")
        if not workspace or not Path(workspace).is_dir():
            print("Project has no workspace.", file=sys.stderr)
            return 1
        result = apply_translations(project, workspace)
        print("Applied %d translations." % result["applied"])
        for path, line, message in result["errors"]:
            print("%s:%s: %s" % (path, line, message), file=sys.stderr)
        return 0 if not result["errors"] else 1
    finally:
        project.close()


def command_build(args):
    project = Project(args.project)
    try:
        workspace = project.get_meta("workspace")
        if not workspace or not Path(workspace).is_dir():
            print("Project has no workspace.", file=sys.stderr)
            return 1
        destination = build_translated(
            project, workspace, args.output, tools=ToolConfig(load_settings()),
            log=lambda message: print(message, flush=True))
        print("Build ready: %s" % destination)
        return 0
    except (BuildError, ToolError, OSError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    finally:
        project.close()


def command_strings(args):
    project = Project(args.project)
    try:
        rows = project.strings(args.status or None)
        for row in rows:
            translation = row["translation"] or "-"
            print("%s\t%s:%s\t%s\t%s" % (
                row["id"], row["relative_path"], row["line"],
                row["original"], translation))
        return 0
    finally:
        project.close()


def command_set(args):
    project = Project(args.project)
    try:
        row = project.get_string(args.string_id)
        if row is None:
            print("String not found.", file=sys.stderr)
            return 1
        for problem in validate_text(row["original"], args.translation):
            print("Warning: %s" % problem, file=sys.stderr)
        project.set_translation(args.string_id, args.translation)
        print("Translation saved.")
        return 0
    finally:
        project.close()


def command_validate(args):
    project = Project(args.project)
    try:
        problems = validate_project(project)
        for string_id, path, line, message in problems:
            print("%s\t%s:%s\t%s" % (string_id, path, line, message))
        print("%d validation problem(s)." % len(problems))
        return 0 if not problems else 2
    finally:
        project.close()


def command_export(args):
    project = Project(args.project)
    try:
        rows = project.strings()
        with Path(args.csv).open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(("id", "file", "line", "original",
                             "translation", "context", "status"))
            for row in rows:
                writer.writerow((row["id"], row["relative_path"],
                                 row["line"], row["original"],
                                 row["translation"], row["context"],
                                 row["status"]))
        print("Exported %d strings." % len(rows))
        return 0
    finally:
        project.close()


def command_import(args):
    project = Project(args.project)
    try:
        count = 0
        with Path(args.csv).open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("id") and row.get("translation") is not None:
                    project.set_translation(int(row["id"]),
                                            row["translation"])
                    count += 1
        print("Imported %d translations." % count)
        return 0
    finally:
        project.close()


def build_parser():
    parser = argparse.ArgumentParser(prog="ddlc-translation-studio")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="Inspect a mod")
    detect.add_argument("mod")
    detect.set_defaults(func=command_detect)

    tools = sub.add_parser("tools", help="Check configured external tools")
    tools.set_defaults(func=command_tools)

    prepare = sub.add_parser("prepare", help="Create a translation workspace")
    prepare.add_argument("mod")
    prepare.add_argument("project")
    prepare.add_argument("--rpa-tool")
    prepare.add_argument("--rpyc-tool")
    prepare.set_defaults(func=command_prepare)

    index = sub.add_parser("index", help="Index scripts in the workspace")
    index.add_argument("project")
    index.set_defaults(func=command_index)

    apply_cmd = sub.add_parser("apply", help="Rewrite scripts in the workspace")
    apply_cmd.add_argument("project")
    apply_cmd.set_defaults(func=command_apply)

    build = sub.add_parser("build", help="Build a translated mod")
    build.add_argument("project")
    build.add_argument("output")
    build.set_defaults(func=command_build)

    strings = sub.add_parser("strings", help="List indexed strings")
    strings.add_argument("project")
    strings.add_argument("--status")
    strings.set_defaults(func=command_strings)

    set_cmd = sub.add_parser("set", help="Set one translation")
    set_cmd.add_argument("project")
    set_cmd.add_argument("string_id", type=int)
    set_cmd.add_argument("translation")
    set_cmd.set_defaults(func=command_set)

    validate_cmd = sub.add_parser("validate", help="Validate translations")
    validate_cmd.add_argument("project")
    validate_cmd.set_defaults(func=command_validate)

    export = sub.add_parser("export", help="Export strings to CSV")
    export.add_argument("project")
    export.add_argument("csv")
    export.set_defaults(func=command_export)

    import_cmd = sub.add_parser("import", help="Import translations from CSV")
    import_cmd.add_argument("project")
    import_cmd.add_argument("csv")
    import_cmd.set_defaults(func=command_import)
    return parser



def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    commands = {"detect", "tools", "prepare", "index", "apply", "build",
                "strings", "set", "validate", "export", "import"}
    if not args:
        from ddlc_translator.gui import run
        return run()
    if args[0] in commands or args[0] in ("-h", "--help"):
        parser = build_parser()
        parsed = parser.parse_args(args)
        return parsed.func(parsed)
    from ddlc_translator.gui import run
    return run(args[0])


if __name__ == "__main__":
    sys.exit(main())

