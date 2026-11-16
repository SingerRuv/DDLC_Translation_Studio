"""Validation for Ren'Py translation strings."""
import re
from collections import Counter

VARIABLE = re.compile(r"\[[^\]]+\]")
TAG = re.compile(r"\{[^}]+\}")
FORMAT = re.compile(r"%(?:\d+\$)?[-+#0 .]*\d*[diouxXeEfFgGcrs]")


def _counts(pattern, text):
    return Counter(pattern.findall(text))


def _has_unescaped_quote(text):
    escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return True
    return False


def validate(original, translation):
    errors = []
    if not translation.strip():
        return ["translation is empty"]
    for name, pattern in (("variable", VARIABLE), ("tag", TAG),
                          ("format", FORMAT)):
        before = _counts(pattern, original)
        after = _counts(pattern, translation)
        if before != after:
            errors.append("%s placeholders differ" % name)
    if original.count("\\n") != translation.count("\\n"):
        errors.append("line breaks differ")
    if _has_unescaped_quote(translation):
        errors.append("double quotes must be escaped")
    return errors


def validate_project(project):
    problems = []
    for row in project.strings():
        for message in validate(row["original"], row["translation"]):
            problems.append((row["id"], row["relative_path"], row["line"],
                             message))
    return problems
