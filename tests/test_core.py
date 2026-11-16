"""Core tests for DDLCTranslationStudio."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ddlc_translator import (build, indexer, modinfo, project, rewrite,
                             tools, validate, workspace)  # noqa: E402


def put(base, rel, data=b"x"):
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def make_mod(base, version=7, rpa=False):
    put(base, "Game.exe", b"launcher")
    put(base, "game/script.rpyc", b"compiled")
    if rpa:
        put(base, "game/scripts.rpa", b"RPA-3.0")
    put(base, "renpy/__init__.py",
        ("version_tuple = (%d, 0, 0, 0)\n" % version).encode())
    (base / "lib" / "py2-windows-x86_64").mkdir(parents=True)


class ModInfoTests(unittest.TestCase):
    def test_find_root_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "My Mod"
            make_mod(mod)
            self.assertEqual(modinfo.find_mod_root(mod), mod.resolve())
            self.assertEqual(modinfo.detect_renpy_version(mod), "7")

    def test_unknown_path(self):
        with self.assertRaises(modinfo.ModInfoError):
            modinfo.find_mod_root("does-not-exist")


class ProjectTests(unittest.TestCase):
    def test_project_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with project.Project(Path(tmp) / "project") as p:
                p.set_meta("language", "es")
                file_id = p.add_file("game/script.rpy", "script")
                self.assertEqual(p.get_meta("language"), "es")
                self.assertEqual(len(p.files()), 1)
                self.assertIsInstance(file_id, int)


class ToolTests(unittest.TestCase):
    def test_command_uses_arguments(self):
        settings = {
            "rpa_extractor": sys.executable,
            "rpa_args": ["-c", "print('ok')"],
            "rpyc_decompiler": sys.executable,
            "rpyc_args": ["-c", "print('ok')"],
        }
        config = tools.ToolConfig(settings)
        command = config.command("rpa_extractor", input="in.rpa",
                                 output="out")
        self.assertEqual(command[0], sys.executable)
        self.assertIn("print('ok')", command)

    def test_output_is_bounded(self):
        settings = {
            "rpa_extractor": sys.executable,
            "rpa_args": ["-c", "for i in range(300): print(i)"],
            "rpyc_decompiler": sys.executable,
            "rpyc_args": ["-c", "pass"],
        }
        output = tools.ToolConfig(settings).run("rpa_extractor")
        self.assertEqual(len(output.splitlines()), 200)


class IndexTests(unittest.TestCase):
    SCRIPT = """label start:
    e "Hello [name]!"
    "Narration {i}ok{/i}"
    menu:
        "Choice A":
            e "Yes"
    show e "happy"
    define e = Character("Eileen")
    e "Escaped \\"quote\\""
"""

    def test_extract_dialogue_and_menu(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script.rpy"
            script.write_text(self.SCRIPT, encoding="utf-8")
            entries = indexer.extract_script(script)
            self.assertEqual([entry["original"] for entry in entries], [
                "Hello [name]!",
                "Narration {i}ok{/i}",
                "Choice A",
                "Yes",
                'Escaped \\"quote\\"',
            ])
            self.assertTrue(all(entry["context"] == "start"
                                for entry in entries))

    def test_index_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            game = workspace_root / "game"
            game.mkdir(parents=True)
            (game / "script.rpy").write_text(self.SCRIPT, encoding="utf-8")
            with project.Project(Path(tmp) / "project") as p:
                stats = indexer.index_workspace(p, workspace_root)
                self.assertEqual(stats, {"files": 1, "strings": 5})
                self.assertEqual(len(p.strings()), 5)

    def test_validation(self):
        self.assertEqual(validate.validate(
            "Hello [name] {i}ok{/i}", "Hola [name] {i}ok{/i}"), [])
        self.assertIn("variable placeholders differ",
                      validate.validate("Hello [name]", "Hola"))
        self.assertIn("tag placeholders differ",
                      validate.validate("{i}Hi{/i}", "Hola"))
        self.assertEqual(validate.validate("Hi", ""),
                         ["translation is empty"])
        self.assertIn("double quotes must be escaped",
                      validate.validate("Hi", 'He said "hi"'))
        self.assertEqual(validate.validate("Hi", 'He said \\"hi\\"'), [])


class RewriteTests(unittest.TestCase):
    def _setup(self, tmp):
        workspace = Path(tmp) / "workspace"
        game = workspace / "game"
        game.mkdir(parents=True)
        script = game / "script.rpy"
        script.write_text(
            'label start:\n    e "Hello [name]!"\n    "Bye"\n',
            encoding="utf-8")
        proj = project.Project(Path(tmp) / "project")
        file_id = proj.add_file("game/script.rpy")
        string_id = proj.add_string(file_id, 2, "Hello [name]!", "start")
        return workspace, script, proj, string_id

    def test_apply_translation(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, script, proj, string_id = self._setup(tmp)
            proj.set_translation(string_id, "Hola [name]!")
            result = rewrite.apply_translations(proj, workspace)
            proj.close()
            self.assertEqual(result["applied"], 1)
            self.assertEqual(result["errors"], [])
            self.assertIn('e "Hola [name]!"', script.read_text(
                encoding="utf-8"))

    def test_invalid_translation_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, script, proj, string_id = self._setup(tmp)
            original = script.read_text(encoding="utf-8")
            proj.set_translation(string_id, "Hola")
            result = rewrite.apply_translations(proj, workspace)
            proj.close()
            self.assertTrue(result["errors"])
            self.assertEqual(script.read_text(encoding="utf-8"), original)

    def test_apply_from_snapshot_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            game = workspace / "game"
            game.mkdir(parents=True)
            script = game / "script.rpy"
            content = 'label start:\n    e "Hello [name]!"\n'
            script.write_text(content, encoding="utf-8")
            snapshot = Path(tmp) / "original"
            (snapshot / "game").mkdir(parents=True)
            shutil.copy2(script, snapshot / "game" / "script.rpy")
            proj = project.Project(Path(tmp) / "project")
            proj.set_meta("snapshot", snapshot)
            file_id = proj.add_file("game/script.rpy")
            string_id = proj.add_string(file_id, 2, "Hello [name]!", "start")
            proj.set_translation(string_id, "Hola [name]!")
            first = rewrite.apply_translations(proj, workspace)
            second = rewrite.apply_translations(proj, workspace)
            proj.close()
            self.assertEqual(first["errors"], [])
            self.assertEqual(second["errors"], [])
            self.assertIn('e "Hola [name]!"', script.read_text(
                encoding="utf-8"))
            self.assertIn('e "Hello [name]!"',
                          (snapshot / "game" / "script.rpy").read_text(
                              encoding="utf-8"))


class FakeTools:
    def compile_project(self, workspace):
        source = Path(workspace) / "game" / "script.rpy"
        source.with_suffix(".rpyc").write_bytes(b"compiled translated")


class BuildTests(unittest.TestCase):
    def test_build_preserves_source_and_adds_compiled_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            make_mod(source, rpa=True)
            put(source, "game/script.rpy",
                b'label start:\n    e "Hello [name]!"\n')
            workspace_dir = Path(tmp) / "workspace"
            workspace.copy_mod(source, workspace_dir)
            proj = project.Project(Path(tmp) / "project")
            proj.set_meta("source", source)
            file_id = proj.add_file("game/script.rpy")
            string_id = proj.add_string(file_id, 2, "Hello [name]!", "start")
            proj.set_translation(string_id, "Hola [name]!")
            output = Path(tmp) / "build"
            result = build.build_translated(
                proj, workspace_dir, output, tools=FakeTools(),
                log=lambda *_: None)
            proj.close()
            self.assertEqual(result, output)
            self.assertTrue((output / "game" / "scripts.rpa").is_file())
            self.assertEqual(
                (output / "game" / "script.rpyc").read_bytes(),
                b"compiled translated")


class WorkspaceTests(unittest.TestCase):
    def test_copy_mod_and_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "mod"
            make_mod(mod, rpa=True)
            dest = Path(tmp) / "project" / "workspace" / "mod"
            workspace.copy_mod(mod, dest)
            self.assertTrue((dest / "game" / "script.rpyc").is_file())
            self.assertEqual(len(workspace.archives(dest)), 1)
            self.assertEqual(len(workspace.scripts(dest)), 1)

    def test_copy_scripts_is_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "mod"
            make_mod(mod, rpa=True)
            dest = Path(tmp) / "workspace"
            workspace.copy_scripts(mod, dest)
            self.assertTrue((dest / "game" / "script.rpyc").is_file())
            self.assertTrue((dest / "game" / "scripts.rpa").is_file())
            self.assertFalse((dest / "renpy").exists())


if __name__ == "__main__":
    unittest.main()
