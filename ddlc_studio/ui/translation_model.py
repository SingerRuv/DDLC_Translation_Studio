"""Qt table model for translation strings."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal

COLUMNS = ("file", "line", "original", "translation", "status")


class TranslationModel(QAbstractTableModel):
    changed = Signal()

    def __init__(self, project, translator, parent=None):
        super().__init__(parent)
        self.project = project
        self.t = translator
        self.rows = []
        self.reload()

    def reload(self):
        self.beginResetModel()
        self.rows = [dict(row) for row in self.project.strings()]
        self.endResetModel()
        self.changed.emit()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal or role != Qt.DisplayRole:
            return None
        return {
            "file": self.t("editor.file"),
            "line": self.t("editor.line"),
            "original": self.t("editor.original"),
            "translation": self.t("editor.translation"),
            "status": self.t("editor.status"),
        }.get(COLUMNS[section], COLUMNS[section])

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        column = COLUMNS[index.column()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            if column == "translation":
                return row["translation"]
            if column == "status":
                return self.t("editor." + row["status"])
            if column == "line":
                return str(row["line"])
            if column == "file":
                return row["relative_path"]
            return row["original"]
        if role == Qt.TextAlignmentRole and column == "line":
            return int(Qt.AlignCenter)
        if role == Qt.ToolTipRole:
            return row["context"] or ""
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if COLUMNS[index.column()] == "translation":
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if (role != Qt.EditRole or not index.isValid() or
                COLUMNS[index.column()] != "translation"):
            return False
        row = self.rows[index.row()]
        translation = str(value)
        self.project.set_translation(row["id"], translation)
        row["translation"] = translation
        row["status"] = "translated" if translation.strip() else "pending"
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        status_index = self.index(index.row(), COLUMNS.index("status"))
        self.dataChanged.emit(status_index, status_index, [Qt.DisplayRole])
        self.changed.emit()
        return True

    def counts(self):
        translated = sum(1 for row in self.rows if row["status"] == "translated")
        return translated, len(self.rows)


class TranslationFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search = ""
        self.status = "all"
        self.file_path = ""

    def set_search(self, text):
        self.search = text.strip().casefold()
        self.invalidateFilter()

    def set_status(self, status):
        self.status = status
        self.invalidateFilter()

    def set_file(self, path):
        self.file_path = path
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        row = model.rows[source_row]
        if self.file_path and row["relative_path"] != self.file_path:
            return False
        if self.status != "all" and row["status"] != self.status:
            return False
        if not self.search:
            return True
        haystack = " ".join((
            row["relative_path"], row["original"], row["translation"],
            row["context"])).casefold()
        return self.search in haystack
