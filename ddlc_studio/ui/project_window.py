"""Main translation editor window with a VS Code-like shell."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QStatusBar,
    QStyle,
    QTableView,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import load_settings
from ..core.csv_io import export_csv, import_csv
from ..core.indexer import index_workspace
from ..core.project import Project
from ..core.validate import validate_project
from .build_result import BuildResultDialog
from .build_worker import BuildThread
from .code_editor import CodePreview
from .translation_model import TranslationFilterProxy, TranslationModel


class ProjectWindow(QMainWindow):
    closed = Signal()

    def __init__(self, project_path, translator, settings=None, parent=None):
        super().__init__(parent)
        self.t = translator
        self.settings = dict(settings or load_settings())
        self.project_path = Path(project_path)
        self.project = Project(self.project_path)
        self.game_root = Path(
            self.project.get_meta("workspace") or
            self.project_path / "workspace" / "game")
        self._build_thread = None
        self._build_progress = None
        self.setWindowTitle("%s - %s" % (self.t("app.title"),
                                         self.project_path.name))
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(1000, 600)
        self.resize(1280, 660)
        self._build_ui()
        self._update_stats()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        activity = QFrame()
        activity.setObjectName("activityBar")
        activity.setFixedWidth(46)
        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(5, 8, 5, 8)
        activity_layout.setSpacing(4)
        self.files_button = self._activity_button(
            QStyle.SP_DirIcon, "Files", self._toggle_explorer, True)
        self.strings_button = self._activity_button(
            QStyle.SP_FileDialogDetailedView, "Strings",
            lambda: self.strings_tabs.setCurrentIndex(0))
        self.build_button = self._activity_button(
            QStyle.SP_MediaPlay, "Build", self.build_mod)
        activity_layout.addWidget(self.files_button)
        activity_layout.addWidget(self.strings_button)
        activity_layout.addWidget(self.build_button)
        activity_layout.addStretch(1)
        outer.addWidget(activity)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(270)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10, 10, 8, 8)
        side_layout.setSpacing(5)
        self.explorer_title = QLabel()
        self.explorer_title.setObjectName("section")
        side_layout.addWidget(self.explorer_title)

        self.explorer = QTreeWidget()
        self.explorer.setHeaderHidden(True)
        self.explorer.setIndentation(14)
        self.explorer.setAnimated(False)
        self.explorer.itemClicked.connect(self._explorer_clicked)
        side_layout.addWidget(self.explorer, 1)
        self._load_script_tree()

        self.all_files_button = QPushButton()
        self.all_files_button.setObjectName("secondary")
        self.all_files_button.clicked.connect(self._show_all_files)
        side_layout.addWidget(self.all_files_button)
        outer.addWidget(self.sidebar)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("editorToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 7, 12, 7)
        toolbar_layout.setSpacing(6)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.title = QLabel(self.project_path.name)
        self.title.setObjectName("section")
        self.path_label = QLabel(str(self.project_path))
        self.path_label.setObjectName("muted")
        titles.addWidget(self.title)
        titles.addWidget(self.path_label)
        toolbar_layout.addLayout(titles, 1)
        self.validate_button = QPushButton()
        self.validate_button.setObjectName("secondary")
        self.validate_button.clicked.connect(self.validate_all)
        self.reindex_button = QPushButton()
        self.reindex_button.setObjectName("secondary")
        self.reindex_button.clicked.connect(self.reindex_project)
        self.export_button = QPushButton()
        self.export_button.setObjectName("secondary")
        self.export_button.clicked.connect(self.export_rows)
        self.import_button = QPushButton()
        self.import_button.setObjectName("secondary")
        self.import_button.clicked.connect(self.import_rows)
        self.build_now_button = QPushButton()
        self.build_now_button.clicked.connect(self.build_mod)
        toolbar_layout.addWidget(self.validate_button)
        toolbar_layout.addWidget(self.reindex_button)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addWidget(self.import_button)
        toolbar_layout.addWidget(self.build_now_button)
        main_layout.addWidget(toolbar)

        self.code_tabs = QTabWidget()
        self.code_tabs.setTabsClosable(True)
        self.code_tabs.setMovable(True)
        self.code_tabs.tabCloseRequested.connect(self._close_preview)
        self._preview_editors = {}

        self.strings_tabs = QTabWidget()
        strings_tab = QWidget()
        strings_layout = QVBoxLayout(strings_tab)
        strings_layout.setContentsMargins(8, 8, 8, 8)
        strings_layout.setSpacing(6)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        filters.addWidget(self.search, 1)
        self.status_filter = QComboBox()
        self.status_filter.addItem(self.t("editor.all"), "all")
        self.status_filter.addItem(self.t("editor.pending"), "pending")
        self.status_filter.addItem(self.t("editor.translated"), "translated")
        filters.addWidget(self.status_filter)
        self.stats = QLabel()
        self.stats.setObjectName("muted")
        filters.addWidget(self.stats)
        strings_layout.addLayout(filters)

        self.model = TranslationModel(self.project, self.t, self)
        self.proxy = TranslationFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.EditKeyPressed |
            QAbstractItemView.SelectedClicked)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.verticalHeader().setVisible(False)
        header_view = self.table.horizontalHeader()
        header_view.setHighlightSections(False)
        header_view.setSectionResizeMode(0, QHeaderView.Interactive)
        header_view.setSectionResizeMode(1, QHeaderView.Interactive)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 55)
        self.table.setColumnWidth(4, 95)
        strings_layout.addWidget(self.table, 1)
        self.strings_tabs.addTab(strings_tab, self.t("editor.strings_tab"))
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.code_tabs)
        splitter.addWidget(self.strings_tabs)
        splitter.setSizes([520, 260])
        main_layout.addWidget(splitter, 1)
        outer.addWidget(main, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_file = QLabel(self.t("editor.all_files"))
        self.status_file.setObjectName("status")
        self.status_sdk = QLabel(
            "Ren'Py %s" % self.project.get_meta("renpy_version"))
        self.status_sdk.setObjectName("status")
        status.addWidget(self.status_file)
        status.addPermanentWidget(self.status_sdk)

        self.retranslate()
        self.search.textChanged.connect(self.proxy.set_search)
        self.status_filter.currentIndexChanged.connect(
            lambda _index: self.proxy.set_status(
                self.status_filter.currentData()))
        self.model.changed.connect(self._update_stats)
        self.table.selectionModel().currentChanged.connect(
            self._table_selection_changed)
        self._open_first_script()

    def _activity_button(self, icon, tooltip, callback, checkable=False):
        button = QToolButton()
        button.setIcon(self.style().standardIcon(icon))
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        if checkable:
            button.setChecked(True)
        button.clicked.connect(callback)
        return button

    def retranslate(self):
        self.explorer_title.setText(self.t("editor.explorer"))
        self.all_files_button.setText(self.t("editor.all_files"))
        self.validate_button.setText(self.t("editor.validate"))
        self.reindex_button.setText(self.t("editor.reindex"))
        self.export_button.setText(self.t("editor.export"))
        self.import_button.setText(self.t("editor.import"))
        self.build_now_button.setText(self.t("editor.build"))
        self.search.setPlaceholderText(self.t("editor.search"))
        self.strings_tabs.setTabText(0, self.t("editor.strings_tab"))
        self.files_button.setToolTip(self.t("editor.explorer"))
        self.strings_button.setToolTip(self.t("editor.strings_tab"))
        self.build_button.setToolTip(self.t("editor.build"))

    def _toggle_explorer(self):
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self.files_button.setChecked(visible)

    def _show_all_files(self):
        self.proxy.set_file("")
        self.status_file.setText(self.t("editor.all_files"))

    def _load_script_tree(self):
        self.explorer.clear()
        folder_icon = self.style().standardIcon(QStyle.SP_DirIcon)
        file_icon = self.style().standardIcon(QStyle.SP_FileIcon)
        nodes = {}
        try:
            files = sorted(
                path for path in self.game_root.rglob("*")
                if path.is_file() and path.suffix.lower() in (".rpy", ".rpym"))
        except OSError:
            files = []
        for path in files:
            relative = path.relative_to(self.game_root)
            parent = self.explorer.invisibleRootItem()
            current = self.game_root
            for part in relative.parts[:-1]:
                current = current / part
                key = str(current)
                item = nodes.get(key)
                if item is None:
                    item = QTreeWidgetItem([part])
                    item.setIcon(0, folder_icon)
                    parent.addChild(item)
                    nodes[key] = item
                parent = item
            item = QTreeWidgetItem([relative.name])
            item.setIcon(0, file_icon)
            item.setData(0, Qt.UserRole, str(path))
            parent.addChild(item)
        self.explorer.expandAll()

    def _explorer_clicked(self, item, _column):
        value = item.data(0, Qt.UserRole)
        if not value:
            return
        path = Path(value)
        if not path.is_file() or self.game_root not in path.parents:
            self._show_all_files()
            return
        relative = path.relative_to(self.game_root).as_posix()
        self.proxy.set_file("game/" + relative)
        self.status_file.setText("game/" + relative)
        self._open_preview(path)

    def _open_preview(self, path, line=None):
        path = Path(path).resolve()
        if not path.is_file() or self.game_root not in path.parents:
            return
        key = str(path)
        editor = self._preview_editors.get(key)
        if editor is None:
            editor = CodePreview(
                dark=self.settings.get("theme", "dark") != "light", parent=self)
            editor.load_file(path)
            index = self.code_tabs.addTab(
                editor, path.relative_to(self.game_root).as_posix())
            self.code_tabs.setTabToolTip(index, str(path))
            self._preview_editors[key] = editor
        self.code_tabs.setCurrentWidget(editor)
        if line:
            editor.highlight_line(line)
        self.status_file.setText(
            "game/" + path.relative_to(self.game_root).as_posix())

    def _close_preview(self, index):
        editor = self.code_tabs.widget(index)
        if editor is None:
            return
        self.code_tabs.removeTab(index)
        for key, value in list(self._preview_editors.items()):
            if value is editor:
                del self._preview_editors[key]
                break
        editor.deleteLater()

    def _table_selection_changed(self, current, _previous):
        if not current.isValid():
            return
        source = self.proxy.mapToSource(current)
        if not source.isValid() or source.row() >= len(self.model.rows):
            return
        row = self.model.rows[source.row()]
        relative = row["relative_path"]
        if not relative.startswith("game/"):
            return
        self._open_preview(self.game_root / relative[5:], row["line"])

    def _open_first_script(self):
        try:
            preferred = self.game_root / "script.rpy"
            if preferred.is_file():
                script = preferred
            else:
                script = next(iter(sorted(self.game_root.rglob("*.rpy"))))
        except (OSError, StopIteration):
            return
        self._open_preview(script)

    def _update_stats(self):
        translated, total = self.model.counts()
        self.stats.setText(self.t("editor.stats", translated=translated,
                                  total=total))

    def reindex_project(self):
        workspace = self.project.get_meta("workspace")
        if not workspace or not Path(workspace).is_dir():
            QMessageBox.warning(self, self.t("common.error"),
                                self.t("project.open_failed"))
            return
        workspace_root = Path(workspace).parent
        try:
            index_workspace(
                self.project, workspace_root, workspace_root, replace=True)
        except Exception as exc:
            QMessageBox.critical(self, self.t("common.error"), str(exc))
            return
        self.model.reload()
        self._update_stats()
        self._show_all_files()
        self.status_file.setText(self.t("editor.all_files"))

    def validate_all(self):
        problems = validate_project(self.project)
        if not problems:
            QMessageBox.information(self, self.t("editor.validation_title"),
                                    self.t("editor.validation_ok"))
            return
        details = "\n".join(
            "%s:%s: %s" % (path, line, message)
            for _id, path, line, message in problems[:20])
        QMessageBox.warning(
            self, self.t("editor.validation_title"),
            self.t("editor.validation_body", count=len(problems),
                   details=details))

    def export_rows(self):
        path, _filter = QFileDialog.getSaveFileName(
            self, self.t("editor.export"), "translations.csv",
            "CSV (*.csv)")
        if not path:
            return
        try:
            count = export_csv(self.project, path)
        except OSError as exc:
            QMessageBox.critical(self, self.t("common.error"), str(exc))
            return
        QMessageBox.information(self, self.t("editor.export"),
                                self.t("editor.exported", count=count))

    def import_rows(self):
        path, _filter = QFileDialog.getOpenFileName(
            self, self.t("editor.import"), "",
            "CSV (*.csv);;All files (*)")
        if not path:
            return
        try:
            count = import_csv(self.project, path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, self.t("editor.csv_error"), str(exc))
            return
        self.model.reload()
        QMessageBox.information(self, self.t("editor.import"),
                                self.t("editor.imported", count=count))

    def build_mod(self):
        if self._build_thread is not None:
            return
        self._build_progress = QProgressDialog(
            self.t("build.running"), None, 0, 0, self)
        self._build_progress.setWindowTitle(self.t("editor.build"))
        self._build_progress.setWindowModality(Qt.WindowModal)
        self._build_progress.setMinimumDuration(0)
        self._build_progress.setCancelButton(None)
        self._build_progress.show()
        self._build_thread = BuildThread(
            self.project_path, self.settings, self)
        self._build_thread.progress.connect(self._build_progress.setLabelText)
        self._build_thread.finished_ok.connect(self._build_done)
        self._build_thread.failed.connect(self._build_failed)
        self._build_thread.start()

    def _build_done(self, result):
        if self._build_progress is not None:
            self._build_progress.close()
            self._build_progress = None
        if self._build_thread is not None:
            self._build_thread.deleteLater()
            self._build_thread = None
        BuildResultDialog(self, result, self.t).exec()

    def _build_failed(self, message):
        if self._build_progress is not None:
            self._build_progress.close()
            self._build_progress = None
        if self._build_thread is not None:
            self._build_thread.deleteLater()
            self._build_thread = None
        QMessageBox.critical(self, self.t("common.error"),
                             "%s\n\n%s" % (self.t("build.failed"), message))

    def closeEvent(self, event):
        self.model.beginResetModel()
        self.model.rows = []
        self.model.endResetModel()
        self.project.close()
        self.closed.emit()
        super().closeEvent(event)






