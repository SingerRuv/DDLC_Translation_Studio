"""Global application settings."""
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import save_settings


class SettingsDialog(QDialog):
    def __init__(self, parent, settings, translator):
        super().__init__(parent)
        self.settings = dict(settings)
        self.t = translator
        self.setWindowTitle(self.t("dialog.settings"))
        self.setMinimumWidth(620)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.language = QComboBox()
        self.language.addItem(self.t("settings.language_es"), "es")
        self.language.addItem(self.t("settings.language_en"), "en")
        index = self.language.findData(self.settings.get("language", "es"))
        self.language.setCurrentIndex(max(index, 0))
        form.addRow(self.t("settings.language"), self.language)

        self.theme = QComboBox()
        self.theme.addItem(self.t("settings.theme_dark"), "dark")
        self.theme.addItem(self.t("settings.theme_light"), "light")
        index = self.theme.findData(self.settings.get("theme", "dark"))
        self.theme.setCurrentIndex(max(index, 0))
        form.addRow(self.t("settings.theme"), self.theme)

        self.sdk_fields = {}
        for key in ("renpy6", "renpy7", "renpy8"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            field = QLineEdit(self.settings.get(key, ""))
            field.setPlaceholderText("renpy.exe")
            browse = QPushButton(self.t("settings.browse"))
            browse.clicked.connect(
                lambda _checked=False, name=key: self._browse(name))
            row_layout.addWidget(field, 1)
            row_layout.addWidget(browse)
            self.sdk_fields[key] = field
            form.addRow(self.t("settings.sdk" + key[-1]), row)

        layout.addLayout(form)
        hint = QLabel(self.t("settings.sdk_hint"))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(
            self.t("settings.save"))
        buttons.button(QDialogButtonBox.Cancel).setText(
            self.t("settings.cancel"))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self, key):
        start = self.sdk_fields[key].text().strip()
        if not start:
            start = str(Path.home() / "Desktop")
        path, _filter = QFileDialog.getOpenFileName(
            self, self.t("settings.sdk" + key[-1]), start,
            "renpy.exe (renpy.exe);;Executables (*.exe);;All files (*)")
        if path:
            self.sdk_fields[key].setText(path)

    def _save(self):
        self.settings["language"] = self.language.currentData()
        self.settings["theme"] = self.theme.currentData()
        for key, field in self.sdk_fields.items():
            self.settings[key] = field.text().strip()
        save_settings(self.settings)
        self.accept()
