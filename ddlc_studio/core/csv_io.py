"""CSV import and export for translation projects."""
import csv
from pathlib import Path


def export_csv(project, path):
    path = Path(path)
    rows = project.strings()
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("id", "file", "line", "original", "translation",
                         "context", "status"))
        for row in rows:
            writer.writerow((row["id"], row["relative_path"], row["line"],
                             row["original"], row["translation"],
                             row["context"], row["status"]))
    return len(rows)


def import_csv(project, path):
    path = Path(path)
    imported = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            translation = row.get("translation")
            if translation is None:
                continue
            string_id = row.get("id")
            if string_id:
                try:
                    target = int(string_id)
                except ValueError:
                    continue
                existing = project.get_string(target)
                if existing is None:
                    continue
                project.set_translation(target, translation)
                imported += 1
    return imported
