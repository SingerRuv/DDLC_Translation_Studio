"""Apply translated strings back to decompiled Ren'Py scripts."""
from pathlib import Path

from .indexer import _literal
from .validate import validate


def _file_rows(project):
    grouped = {}
    for row in project.strings():
        if not row["translation"].strip():
            continue
        grouped.setdefault(row["relative_path"], []).append(row)
    return grouped


def apply_translations(project, workspace, source=None):
    workspace = Path(workspace).resolve()
    source = Path(source or project.get_meta("snapshot") or workspace).resolve()
    grouped = _file_rows(project)
    pending = {}
    errors = []
    applied = 0
    skipped = 0
    for relative, rows in grouped.items():
        source_path = (source / relative).resolve()
        target = (workspace / relative).resolve()
        if source not in source_path.parents or not source_path.is_file():
            errors.append((relative, 0, "source script not found"))
            continue
        if workspace not in target.parents:
            errors.append((relative, 0, "target script outside workspace"))
            continue
        lines = source_path.read_text(encoding="utf-8-sig").splitlines(
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
            for problem in validate(row["original"], row["translation"]):
                errors.append((relative, number, problem))
            found = _literal(lines[number - 1])
            if found is None:
                errors.append((relative, number, "quoted string not found"))
                continue
            original, start, end = found
            if original != row["original"]:
                errors.append((relative, number, "source text changed"))
                continue
            replacement = row["translation"].replace("\n", "\\n")
            lines[number - 1] = (lines[number - 1][:start + 1] +
                                 replacement + lines[number - 1][end - 1:])
            applied += 1
        pending[target] = "".join(lines)
    if errors:
        return {"applied": applied, "skipped": skipped, "errors": errors}
    for path, content in pending.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"applied": applied, "skipped": skipped, "errors": []}
