"""Extract translatable strings from decompiled Ren'Py scripts."""
import re
from pathlib import Path

RESERVED = {
    "add", "at", "bar", "button", "call", "camera", "config", "contains",
    "default", "define", "elif", "else", "expression", "fixed", "for",
    "frame", "grid", "hide", "hbox", "hotspot", "if", "image", "imagebutton",
    "imagemap", "init", "jump", "key", "label", "layeredimage", "menu", "nvl",
    "on", "pass", "pause", "play", "python", "queue", "renpy", "return",
    "scene", "screen", "show", "side", "style", "text", "textbutton", "timer",
    "transform", "translate", "use", "vbox", "viewport", "voice", "while",
    "window", "with", "$", "-",
}
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _literal(line):
    in_quote = None
    start = None
    escaped = False
    for index, char in enumerate(line):
        if in_quote is None:
            if char == "#":
                return None
            if char in ("'", '"'):
                in_quote = char
                start = index
        elif escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == in_quote:
            return line[start + 1:index], start, index + 1
    return None


def _allowed_prefix(prefix):
    prefix = prefix.strip()
    if not prefix:
        return True
    tokens = prefix.split()
    first = tokens[0].lower()
    if first in RESERVED:
        return False
    return all(IDENTIFIER.match(token) for token in tokens)


def extract_line(line):
    found = _literal(line)
    if found is None:
        return None
    text, start, _end = found
    if not text.strip():
        return None
    if not _allowed_prefix(line[:start]):
        return None
    return text


def extract_script(path):
    path = Path(path)
    entries = []
    label = ""
    for number, line in enumerate(
            path.read_text(encoding="utf-8-sig", errors="ignore").splitlines(),
            1):
        stripped = line.strip()
        if stripped.startswith("label "):
            label = stripped[6:].split("(", 1)[0].rstrip(":").strip()
        text = extract_line(line)
        if text is not None:
            entries.append({
                "line": number,
                "original": text,
                "context": label,
            })
    return entries


def index_workspace(project, workspace, source=None):
    source_root = Path(source or workspace)
    game = source_root / "game"
    files = 0
    strings = 0
    with project.transaction():
        for script in sorted(game.rglob("*.rpy")):
            relative = script.relative_to(source_root)
            if "tl" in relative.parts:
                continue
            file_id = project.add_file(relative, kind="script", commit=False)
            files += 1
            for entry in extract_script(script):
                project.add_string(file_id, entry["line"], entry["original"],
                                   entry["context"], commit=False)
                strings += 1
    return {"files": files, "strings": strings}
