"""External tool configuration and execution."""
from collections import deque
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from .config import load_settings

MAX_OUTPUT_LINES = 200
MAX_OUTPUT_LINE = 2000

class ToolError(Exception):
    pass


def _resolve_executable(value):
    path = Path(str(value))
    if path.is_file():
        if path.suffix.lower() == ".py":
            return [sys.executable, str(path)]
        return [str(path)]
    found = shutil.which(str(value))
    if found:
        return [found]
    raise ToolError("Tool not found: %s" % value)


def _format_args(template, values):
    result = []
    for item in template:
        result.append(str(item).format(**values))
    return result


def _read_stream(stream, tail):
    try:
        for line in iter(stream.readline, ""):
            tail.append(line.rstrip("\n")[:MAX_OUTPUT_LINE])
    finally:
        stream.close()


class ToolConfig:
    def __init__(self, settings=None):
        self.settings = dict(settings or load_settings())

    def command(self, name, **values):
        executable = self.settings.get(name)
        args_key = {"rpa_extractor": "rpa_args",
                    "rpyc_decompiler": "rpyc_args",
                    "renpy": "renpy_args"}.get(name, "")
        args = self.settings.get(args_key, [])
        if not executable:
            raise ToolError("No executable configured for %s." % name)
        return _resolve_executable(executable) + _format_args(args, values)

    def validate(self):
        for name in ("rpa_extractor", "rpyc_decompiler"):
            self.command(name, input="x", output="x")
        return True

    def run(self, name, cwd=None, **values):
        command = self.command(name, **values)
        try:
            process = subprocess.Popen(
                command, cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as exc:
            raise ToolError("Could not run %s: %s" % (name, exc))
        output_tail = deque(maxlen=MAX_OUTPUT_LINES)
        error_tail = deque(maxlen=MAX_OUTPUT_LINES)
        readers = (
            threading.Thread(target=_read_stream,
                             args=(process.stdout, output_tail), daemon=True),
            threading.Thread(target=_read_stream,
                             args=(process.stderr, error_tail), daemon=True),
        )
        for reader in readers:
            reader.start()
        process.wait()
        for reader in readers:
            reader.join()
        detail = "\n".join(error_tail or output_tail).strip()
        if process.returncode:
            raise ToolError("%s failed: %s" % (name, detail))
        return "\n".join(output_tail)

    def extract_rpa(self, archive, output, cwd=None):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        return self.run("rpa_extractor", cwd=cwd, input=str(archive),
                        output=str(output))

    def decompile_rpyc(self, script, cwd=None):
        script = Path(script)
        return self.run("rpyc_decompiler", cwd=cwd or script.parent,
                        input=str(script))

    def compile_project(self, project, cwd=None):
        return self.run("renpy", cwd=cwd, project=str(project))


