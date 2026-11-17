"""Initial window with project actions and recent projects."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import save_settings
from ..core.projects import summary_from_path
from ..theme import apply_theme
from .project_window import ProjectWindow
from .project_worker import ProjectThread
from .settings_dialog import SettingsDialog
from .wizard import NewProjectWizard


class StartWindow(QMainWindow):
    def __init__(self, settings, translator):
        super().__init__()
        self.settings = settings
        self.t = translator
        self._project_thread = None
        self._progress = None
        self._project_window = None
        self.setMinimumSize(900, 620)
        self.resize(980, 680)
        self._build_ui()
        self.apply_theme()
        self.retranslate()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(48, 42, 48, 42)
        outer.setSpacing(16)

        header = QHBoxLayout()
        headings = QVBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        headings.addWidget(self.title)
        headings.addWidget(self.subtitle)
        header.addLayout(headings, 1)
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self.open_settings)
        header.addWidget(self.settings_button, 0, Qt.AlignTop)
        outer.addLayout(header)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(12)

        self.new_button = QPushButton()
        self.new_button.setObjectName("primary")
        self.new_button.setMinimumHeight(42)
        self.new_button.clicked.connect(self.new_project)
        card_layout.addWidget(self.new_button)

        self.open_button = QPushButton()
        self.open_button.setMinimumHeight(42)
        self.open_button.clicked.connect(self.open_project)
        card_layout.addWidget(self.open_button)

        self.hint = QLabel()
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        card_layout.addWidget(self.hint)
        outer.addWidget(card)

        self.recent_title = QLabel()
        self.recent_title.setObjectName("section")
        outer.addWidget(self.recent_title)

        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(150)
        self.recent_list.itemDoubleClicked.connect(self._open_recent)
        outer.addWidget(self.recent_list, 1)

        self.empty_label = QLabel()
        self.empty_label.setObjectName("muted")
        outer.addWidget(self.empty_label)
        self._load_recent()

    def _load_recent(self):
        self.recent_list.clear()
        recent = self.settings.get("recent_projects", [])
        for entry in recent:
            if isinstance(entry, dict):
                label = entry.get("name") or entry.get("path", "")
                path = entry.get("path", "")
            else:
                label = path = str(entry)
            if path:
                from PySide6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, path)
                self.recent_list.addItem(item)
        has_recent = self.recent_list.count() > 0
        self.recent_list.setVisible(has_recent)
        self.empty_label.setVisible(not has_recent)

    def retranslate(self):
        self.setWindowTitle(self.t("app.title"))
        self.title.setText(self.t("app.title"))
        self.subtitle.setText(self.t("start.subtitle"))
        self.settings_button.setText(self.t("start.settings"))
        self.new_button.setText(self.t("start.new"))
        self.open_button.setText(self.t("start.open"))
        self.hint.setText(self.t("start.new_hint"))
        self.recent_title.setText(self.t("start.recent"))
        self.empty_label.setText(self.t("start.empty"))

    def apply_theme(self):
        apply_theme(QApplication.instance(), self.settings.get("theme", "dark"))

    def new_project(self):
        wizard = NewProjectWizard(self, self.t, self.settings)
        if not wizard.exec():
            return
        base = wizard.base_path
        source = wizard.source_path
        self.settings["last_base"] = base
        save_settings(self.settings)
        self._start_project(base, source)

    def _start_project(self, base, source):
        if self._project_thread is not None:
            return
        self._progress = QProgressDialog(
            self.t("project.preparing"), None, 0, 0, self)
        self._progress.setWindowTitle(self.t("wizard.title"))
        self._progress.setWindowModality(Qt.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.setCancelButton(None)
        self._progress.show()
        self._project_thread = ProjectThread(
            base, source, self.settings, self)
        self._project_thread.progress.connect(self._progress.setLabelText)
        self._project_thread.finished_ok.connect(self._project_done)
        self._project_thread.failed.connect(self._project_failed)
        self._project_thread.start()

    def _project_done(self, summary):
        if self._progress is not None:
            self._progress.close()
            self._progress = None
        if self._project_thread is not None:
            self._project_thread.deleteLater()
            self._project_thread = None
        self._add_recent(summary)
        self._open_project_path(summary["path"])

    def _project_failed(self, message):
        if self._progress is not None:
            self._progress.close()
            self._progress = None
        if self._project_thread is not None:
            self._project_thread.deleteLater()
            self._project_thread = None
        QMessageBox.critical(self, self.t("common.error"),
                             "%s\n\n%s" % (self.t("project.failed"), message))

    def _add_recent(self, summary):
        recent = [entry for entry in self.settings.get("recent_projects", [])
                  if (entry.get("path") if isinstance(entry, dict)
                      else str(entry)) != summary["path"]]
        recent.insert(0, {"name": summary["name"], "path": summary["path"]})
        self.settings["recent_projects"] = recent[:8]
        save_settings(self.settings)
        self._load_recent()

    def open_project(self):
        path = QFileDialog.getExistingDirectory(
            self, self.t("start.open_title"),
            str(Path.home() / "DDLC Translation Studio Projects"))
        if path:
            self._open_project_path(path)

    def _open_recent(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self._open_project_path(path)

    def _open_project_path(self, path):
        if self._project_window is not None:
            self._project_window.close()
            self._project_window = None
        try:
            summary_from_path(path)
            window = ProjectWindow(path, self.t, self.settings, self)
        except Exception as exc:
            QMessageBox.critical(self, self.t("common.error"),
                                 "%s\n\n%s" % (
                                     self.t("project.open_failed"), exc))
            return
        window.closed.connect(self._project_closed)
        self._project_window = window
        self.hide()
        window.show()

    def _project_closed(self):
        self._project_window = None
        self.show()
        self.raise_()
        self.activateWindow()

    def open_settings(self):
        dialog = SettingsDialog(self, self.settings, self.t)
        if dialog.exec():
            self.settings.update(dialog.settings)
            self.t.set_language(self.settings.get("language", "es"))
            self.apply_theme()
            self.retranslate()

