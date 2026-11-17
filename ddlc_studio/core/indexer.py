"""Index visible Ren'Py text while ignoring technical strings."""
import re
from pathlib import Path

RESERVED = {
    "add", "at", "bar", "button", "call", "camera", "config", "contains",
    "default", "define", "elif", "else", "expression", "fixed", "for",
    "frame", "grid", "hide", "hbox", "hotspot", "if", "image", "imagebutton",
    "imagemap", "init", "jump", "key", "label", "layeredimage", "menu",
    "on", "pass", "pause", "play", "python", "queue", "renpy", "return",
    "scene", "screen", "show", "side", "style", "style_prefix",
    "style_suffix", "timer", "transform", "translate", "use", "vbox",
    "viewport", "voice", "while", "window", "with", "id", "action",
    "value", "selected", "sensitive", "hovered", "unhovered", "has",
    "fit", "vertical", "radio", "slider", "contain", "$", "-",
}
ALLOWED_KEYWORDS = {"text", "textbutton", "tooltip", "extend", "nvl",
                     "centered", "vcentered"}
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
ASSET_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ogg",
                    ".mp3", ".wav", ".opus", ".ttf", ".otf", ".rpy",
                    ".rpyc", ".rpym", ".rpymc", ".rpa", ".webm")
ASSET_PREFIXES = ("images/", "audio/", "fonts/", "gui/", "game/",
                  "renpy/", "lib/")
COLOR = re.compile(r"^#[0-9A-Fa-f]{3,8}$")


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
            return line[start + 1:index], start
    return None


def _technical(text):
    value = text.strip()
    if not value:
        return True
    if COLOR.match(value):
        return True
    if value.startswith(ASSET_PREFIXES):
        return True
    if value.lower().endswith(ASSET_EXTENSIONS):
        return True
    if ("/" in value or "\\" in value) and not any(
            char.isspace() for char in value):
        return True
    if value.startswith("[") and value.endswith("]") and " " not in value:
        return True
    return False


def _allowed(prefix, line):
    prefix = prefix.strip()
    stripped = line.strip()
    first = prefix.split()[0].lower() if prefix else ""
    if not prefix:
        return True
    if first in ALLOWED_KEYWORDS:
        return True
    if first in RESERVED:
        if stripped.startswith("define ") and (
                "Character(" in prefix or prefix.rstrip().endswith("_(")):
            if "DynamicCharacter(" in prefix:
                return False
            return True
        if stripped.startswith("menu ") and first == "menu":
            return True
        return False
    tokens = prefix.split()
    return all(IDENTIFIER.match(token) for token in tokens)


def extract_line(line):
    found = _literal(line)
    if found is None:
        return None
    text, start = found
    if _technical(text):
        return None
    if not _allowed(line[:start], line):
        return None
    return text


def _brace_delta(line):
    depth = 0
    quote = None
    escaped = False
    for char in line:
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "#":
            break
        if char in ("'", '"'):
            quote = char
        elif char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
    return depth


def extract_script(path):
    path = Path(path)
    entries = []
    label = ""
    screen = ""
    python_indent = None
    python_bracket_depth = 0
    visual_indent = None
    block_depth = 0
    for number, line in enumerate(
            path.read_text(encoding="utf-8-sig", errors="ignore").splitlines(),
            1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if block_depth:
            block_depth = max(0, block_depth + _brace_delta(line))
            continue
        if visual_indent is not None:
            if stripped and indent <= visual_indent:
                visual_indent = None
            else:
                continue
        if python_indent is not None:
            if python_bracket_depth:
                python_bracket_depth = max(
                    0, python_bracket_depth + _brace_delta(line))
                continue
            if stripped and indent <= python_indent:
                python_indent = None
            else:
                python_bracket_depth = max(0, _brace_delta(line))
                continue
        if (stripped.startswith("python:") or
                (stripped.startswith("init ") and "python:" in stripped)):
            python_indent = indent
            python_bracket_depth = 0
            continue
        if (stripped.startswith("define ") or
                stripped.startswith("default ")) and "=" in stripped:
            depth = _brace_delta(line.split("=", 1)[1])
            if depth > 0:
                block_depth = depth
                continue
        if (stripped.startswith(("image ", "transform ", "style "))
                and stripped.endswith(":")):
            visual_indent = indent
            continue
        if stripped.startswith("label "):
            label = stripped[6:].split("(", 1)[0].rstrip(":").strip()
        if stripped.startswith("screen ") and stripped.endswith(":"):
            screen = stripped[7:].split("(", 1)[0].rstrip(":").strip()
        text = extract_line(line)
        if text is not None:
            entries.append({
                "line": number,
                "original": text,
                "context": screen or label,
            })
    return entries


def index_workspace(project, workspace, source=None, replace=False):
    source_root = Path(source or workspace)
    game = source_root / "game"
    saved = {}
    if replace:
        for row in project.strings():
            if row["translation"].strip():
                saved[(row["relative_path"], row["line"],
                       row["original"])] = row["translation"]
    files = 0
    strings = 0
    with project.transaction():
        if replace:
            project.db.execute("DELETE FROM strings")
            project.db.execute("DELETE FROM files")
        for script in sorted(game.rglob("*.rpy")):
            relative = script.relative_to(source_root)
            if "tl" in relative.parts:
                continue
            file_id = project.add_file(relative, kind="script", commit=False)
            files += 1
            for entry in extract_script(script):
                string_id = project.add_string(
                    file_id, entry["line"], entry["original"],
                    entry["context"], commit=False)
                saved_translation = saved.get((
                    relative.as_posix(), entry["line"], entry["original"]))
                if saved_translation:
                    project.set_translation(string_id, saved_translation)
                strings += 1
    return {"files": files, "strings": strings}


