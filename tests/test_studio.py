"""Tests for the new Qt-era project core."""
import pickle
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ddlc_studio.core import modinfo  # noqa: E402
from ddlc_studio.core.csv_io import export_csv, import_csv  # noqa: E402
import ddlc_studio.core.build as build_core  # noqa: E402
from ddlc_studio.core.build import build_project  # noqa: E402
from ddlc_studio.core.indexer import extract_script, index_workspace  # noqa: E402
from ddlc_studio.core.project import Project  # noqa: E402
from ddlc_studio.core.projects import create_project, summary_from_path  # noqa: E402
from ddlc_studio.core.rewrite import apply_translations  # noqa: E402
from ddlc_studio.core.validate import validate  # noqa: E402


def put(base, rel, data=b"x"):
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def make_rpa(path, entries, key=0x42424242):
    header = b"RPA-3.0 " + ("%016x" % 0).encode() + b" " + \
             ("%08x" % key).encode() + b"\n"
    payload = b""
    index = {}
    for name, data in entries:
        offset = len(header) + len(payload)
        payload += data
        index[name] = [(offset ^ key, len(data) ^ key, b"")]
    index_offset = len(header) + len(payload)
    header = b"RPA-3.0 " + ("%016x" % index_offset).encode() + b" " + \
             ("%08x" % key).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + payload + zlib.compress(pickle.dumps(index)))


def make_base(root):
    put(root, "DDLC.exe", b"launcher")
    (root / "lib").mkdir()
    (root / "renpy").mkdir()
    (root / "game" / "python-packages").mkdir(parents=True)
    put(root, "game/python-packages/singleton.py", b"")
    put(root, "renpy/__init__.py", b"version_tuple = (6, 99, 12, 4, 0)\n")
    for name in ("scripts", "images", "audio", "fonts"):
        make_rpa(root / "game" / (name + ".rpa"), [
            (name + ".txt", b"base")])


def make_source(root):
    put(root, "Game.exe", b"launcher")
    (root / "lib").mkdir()
    (root / "renpy").mkdir()
    (root / "game").mkdir()
    put(root, "renpy/__init__.py", b"version_tuple = (7, 5, 3, 0)\n")
    put(root, "game/script.rpy", b"""
label start:
    e "Hello [name]!"
    "Narration"
    menu:
        "Choice A":
            e "Yes"
    show e "happy"
    play music "audio/theme.ogg"
""")


class IndexerTests(unittest.TestCase):
    def test_visible_text_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "screen.rpy"
            script.write_text("""
label start:
    e "Hello [name]!"
    "Narration {i}ok{/i}"
    menu:
        "Choice A":
            e "Yes"
    show e "happy"
    play music "audio/theme.ogg"
    $ secret = "technical"
    define e = Character("Eileen")
    define config.name = _("My Game")
    screen preferences():
        text "Settings"
        textbutton "Start" action Start()
        text "#FFF"
        add "images/background.png"
""", encoding="utf-8")
            entries = extract_script(script)
            self.assertEqual([entry["original"] for entry in entries], [
                "Hello [name]!",
                "Narration {i}ok{/i}",
                "Choice A",
                "Yes",
                "Eileen",
                "My Game",
                "Settings",
                "Start",
            ])


class SourceValidationTests(unittest.TestCase):
    def test_accepts_overlay_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "overlay"
            make_rpa(source / "game" / "scripts.rpa", [
                ("script.rpy", b'label start:\n    "Hi"\n')])
            make_rpa(source / "game" / "mod_assets.rpa", [
                ("picture.png", b"png")])
            root, version, kind = modinfo.validate_source(source)
            self.assertEqual(root, source.resolve())
            self.assertEqual(version, "")
            self.assertEqual(kind, "overlay")

    def test_accepts_compiled_source_with_script_rpa(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "compiled"
            put(source, "Game.exe", b"launcher")
            (source / "lib").mkdir()
            (source / "renpy").mkdir()
            (source / "game").mkdir()
            put(source, "renpy/__init__.py",
                b"version_tuple = (7, 5, 3, 0)\n")
            make_rpa(source / "game" / "scripts.rpa", [
                ("script.rpyc", b"compiled")])
            root, version, kind = modinfo.validate_source(source)
            self.assertEqual(root, source.resolve())
            self.assertEqual(version, "7")
            self.assertEqual(kind, "runtime")


class ValidationTests(unittest.TestCase):
    def test_placeholders_tags_and_quotes(self):
        self.assertEqual(validate("Hello [name] {i}ok{/i}",
                                  "Hola [name] {i}ok{/i}"), [])
        self.assertIn("variable placeholders differ",
                      validate("Hello [name]", "Hola"))
        self.assertIn("tag placeholders differ",
                      validate("{i}Hi{/i}", "Hola"))
        self.assertIn("double quotes must be escaped",
                      validate("Hi", 'He said "hi"'))


class RewriteTests(unittest.TestCase):
    def test_applies_translation_from_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            source = Path(tmp) / "source"
            project_dir = Path(tmp) / "project"
            make_base(base)
            make_source(source)
            create_project(base, source, project_dir)
            project = Project(project_dir)
            try:
                row = project.strings()[0]
                project.set_translation(row["id"], "Hola [name]!")
                result = apply_translations(
                    project, project_dir / "workspace",
                    project_dir / "workspace" / "original")
                self.assertEqual(result["errors"], [])
                text = (project_dir / "workspace" / "game" /
                        "script.rpy").read_text(encoding="utf-8")
                self.assertIn('e "Hola [name]!"', text)
            finally:
                project.close()


class CSVTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            source = Path(tmp) / "source"
            project_dir = Path(tmp) / "project"
            csv = Path(tmp) / "translations.csv"
            make_base(base)
            make_source(source)
            create_project(base, source, project_dir)
            project = Project(project_dir)
            try:
                row = project.strings()[0]
                project.set_translation(row["id"], "Hola")
                self.assertEqual(export_csv(project, csv), 4)
                project.set_translation(row["id"], "")
                self.assertEqual(import_csv(project, csv), 4)
                self.assertEqual(project.get_string(row["id"])["translation"],
                                 "Hola")
            finally:
                project.close()


class BuildTests(unittest.TestCase):
    def test_build_copies_assets_compiles_and_keeps_modified_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            source = Path(tmp) / "source"
            project_dir = Path(tmp) / "project"
            mods = Path(tmp) / "mods"
            make_base(base)
            make_source(source)
            put(source, "game/other.rpy",
                b'label other:\n    "Other text"\n')
            (source / "lib" / "py3-windows-x86_64").mkdir(parents=True,
                                                          exist_ok=True)
            fake_sdk = Path(tmp) / "fake_sdk.bat"
            fake_sdk.write_text(
                '@echo off\r\n'
                'for %%f in ("%~1\\game\\*.rpy") do '
                'copy /Y "%%f" "%%~dpnf.rpyc" >nul\r\n',
                encoding="ascii")
            create_project(base, source, project_dir)
            project = Project(project_dir)
            try:
                row = next(row for row in project.strings()
                           if row["relative_path"].endswith("script.rpy"))
                project.set_translation(row["id"], "Hola [name]!")
            finally:
                project.close()
            old_root = build_core.MODS_ROOT
            build_core.MODS_ROOT = mods
            try:
                result = build_project(
                    project_dir, {"renpy7": str(fake_sdk)},
                    log=lambda _message: None)
            finally:
                build_core.MODS_ROOT = old_root
            game = Path(result["path"]) / "game"
            self.assertEqual(sorted(path.name for path in game.glob("*.rpa")),
                             ["audio.rpa", "fonts.rpa", "images.rpa"])
            self.assertTrue((game / "script.rpyc").is_file())
            self.assertTrue((game / "script.rpy").is_file())
            self.assertFalse((game / "other.rpy").exists())
            self.assertTrue((game / "other.rpyc").is_file())
            self.assertFalse((game / "scripts.rpa").exists())
            self.assertEqual(result["launcher"].name, "Game.exe")


class OverlayTests(unittest.TestCase):
    def test_overlay_uses_base_runtime_and_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            source = Path(tmp) / "overlay"
            project_dir = Path(tmp) / "project"
            mods = Path(tmp) / "mods"
            make_base(base)
            make_rpa(source / "game" / "scripts.rpa", [
                ("script.rpy", b'label start:\n    "Hello"\n')])
            make_rpa(source / "game" / "mod_assets.rpa", [
                ("picture.png", b"png")])
            fake_sdk = Path(tmp) / "fake_sdk.bat"
            fake_sdk.write_text(
                '@echo off\r\n'
                'for %%f in ("%~1\\game\\*.rpy") do '
                'copy /Y "%%f" "%%~dpnf.rpyc" >nul\r\n',
                encoding="ascii")
            summary = create_project(base, source, project_dir)
            self.assertEqual(summary["kind"], "overlay")
            self.assertEqual(summary["version"], "6")
            project = Project(project_dir)
            try:
                self.assertEqual(project.get_meta("runtime_source"),
                                 str(base.resolve()))
                row = project.strings()[0]
                project.set_translation(row["id"], "Hola")
            finally:
                project.close()
            old_root = build_core.MODS_ROOT
            build_core.MODS_ROOT = mods
            try:
                result = build_project(
                    project_dir, {"renpy6": str(fake_sdk)},
                    log=lambda _message: None)
            finally:
                build_core.MODS_ROOT = old_root
            game = Path(result["path"]) / "game"
            self.assertEqual(sorted(path.name for path in game.glob("*.rpa")),
                             ["audio.rpa", "fonts.rpa", "images.rpa"])
            self.assertTrue((game / "script.rpyc").is_file())
            self.assertTrue(
                (game / "python-packages" / "singleton.py").is_file())
            self.assertFalse((game / "scripts.rpa").exists())
            self.assertEqual(result["launcher"].name, "DDLC.exe")


class IndexerBlockTests(unittest.TestCase):
    def test_ignores_define_dict_and_image_atl_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "config.rpy"
            script.write_text("""
define -970 discord_config.large_images = {
    "game_icon": "main_icon",
    "menu": "menu_background",
}

image intro:
    truecenter
    "white"
    0.5

label start:
    "Visible text"
""", encoding="utf-8")
            self.assertEqual(
                [entry["original"] for entry in extract_script(script)],
                ["Visible text"])


class ReindexTests(unittest.TestCase):
    def test_reindex_preserves_translation_and_updates_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            source = Path(tmp) / "source"
            project_dir = Path(tmp) / "project"
            make_base(base)
            make_source(source)
            put(source, "game/config.rpy",
                b'define config.data = {\n    "technical": "value",\n}\n')
            create_project(base, source, project_dir)
            project = Project(project_dir)
            try:
                row = project.strings()[0]
                project.set_translation(row["id"], "Traducido")
                before = len(project.strings())
                stats = index_workspace(
                    project, project_dir / "workspace",
                    project_dir / "workspace", replace=True)
                self.assertLess(stats["strings"], before + 1)
                found = [row for row in project.strings()
                         if row["translation"] == "Traducido"]
                self.assertEqual(len(found), 1)
            finally:
                project.close()


class ProjectTests(unittest.TestCase):
    def test_project_creation_extracts_and_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            source = Path(tmp) / "source"
            project = Path(tmp) / "project"
            make_base(base)
            make_source(source)
            make_rpa(source / "game" / "assets.rpa", [
                ("images/picture.png", b"png"),
                ("data.txt", b"data"),
            ])
            self.assertEqual(modinfo.validate_base(base), base.resolve())
            root, version, kind = modinfo.validate_source(source)
            self.assertEqual(root, source.resolve())
            self.assertEqual(version, "7")
            self.assertEqual(kind, "runtime")
            summary = create_project(base, source, project)
            self.assertEqual(summary["strings"], 4)
            self.assertEqual(summary["files"], 1)
            workspace = project / "workspace" / "game"
            self.assertFalse(list(workspace.rglob("*.rpa")))
            self.assertTrue((workspace / "images" / "picture.png").is_file())
            self.assertFalse((workspace / "lib").exists())
            self.assertTrue((project / "project.sqlite3").is_file())
            existing = create_project(base, source, project)
            self.assertEqual(existing["strings"], 4)
            self.assertEqual(summary_from_path(project)["version"], "7")


if __name__ == "__main__":
    unittest.main()





