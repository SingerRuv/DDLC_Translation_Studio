"""Apply translated strings to the workspace scripts."""
from pathlib import Path

from .indexer import _literal


def translated_files(project):
    return sorted({row["relative_path"] for row in project.strings()
                   if row["translation"].strip()})


def apply_translations(project, workspace_root, source_root=None):
    workspace_root = Path(workspace_root).resolve()
    source_root = Path(source_root or project.get_meta("snapshot") or
                       workspace_root).resolve()
    grouped = {}
    for row in project.strings():
        if row["translation"].strip():
            grouped.setdefault(row["relative_path"], []).append(row)
    pending = {}
    errors = []
    applied = 0
    for relative, rows in grouped.items():
        source = (source_root / relative).resolve()
        target = (workspace_root / relative).resolve()
        if source_root not in source.parents or not source.is_file():
            errors.append((relative, 0, "source script not found"))
            continue
        if workspace_root not in target.parents:
            errors.append((relative, 0, "target outside workspace"))
            continue
        lines = source.read_text(encoding="utf-8-sig").splitlines(
            keepends=True)
        by_line = {}
        for row in rows:
            if row["line"] in by_line:
                errors.append((relative, row["line"],
                               "multiple strings on the same line"))
                continue
            by_line[row["line"]] = row
        for number, row in sorted(by_line.items()):
            if number < 1 or number > len(lines):
                errors.append((relative, number, "line out of range"))
                continue
            found = _literal(lines[number - 1])
            if found is None:
                errors.append((relative, number, "quoted string not found"))
                continue
            original, start = found
            if original != row["original"]:
                errors.append((relative, number, "source text changed"))
                continue
            replacement = row["translation"].replace("\n", "\\n")
            closing_quote = start + len(original) + 1
            lines[number - 1] = (lines[number - 1][:start + 1] +
                                 replacement + lines[number - 1][closing_quote:])
            applied += 1
        pending[target] = "".join(lines)
    if errors:
        return {"applied": applied, "errors": errors}
    for path, content in pending.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"applied": applied, "errors": []}
