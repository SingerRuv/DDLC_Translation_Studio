"""Bundled .rpyc decompiler."""
import subprocess
import sys
from pathlib import Path

from ..vendor.unrpyc import Context, decompile_rpyc


class DecompileError(Exception):
    pass


def decompile(script, overwrite=True):
    script = Path(script)
    context = Context()
    try:
        decompile_rpyc(script, context, overwrite=overwrite)
    except Exception as exc:
        raise DecompileError("Could not decompile %s: %s" %
                             (script.name, exc)) from exc
    suffix = ".rpym" if script.suffix.lower() == ".rpymc" else ".rpy"
    target = script.with_suffix(suffix)
    if context.state == "skip":
        return target
    if context.state != "ok":
        detail = "\n".join(context.log_contents[-5:]).strip()
        raise DecompileError("Could not decompile %s%s" %
                             (script.name, ":\n" + detail if detail else ""))
    return target


def _legacy_script():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "ddlc_studio" / "vendor" / "unrpyc_legacy" / "unrpyc.py"


def decompile_legacy(script, python, log=None):
    script = Path(script)
    legacy = _legacy_script()
    if not legacy.is_file():
        raise DecompileError("Legacy unrpyc is missing.")
    command = [str(python), "-O", str(legacy), str(script)]
    try:
        process = subprocess.run(
            command, cwd=str(script.parent), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", creationflags=0x08000000)
    except OSError as exc:
        raise DecompileError("Could not run legacy unrpyc: %s" % exc) from exc
    tail = "\n".join(process.stdout.splitlines()[-10:])
    if log and tail:
        log(tail)
    target = script.with_suffix(
        ".rpym" if script.suffix.lower() == ".rpymc" else ".rpy")
    if process.returncode or not target.is_file():
        raise DecompileError("Legacy unrpyc failed for %s%s" %
                             (script.name, ":\n" + tail if tail else ""))
    return target
