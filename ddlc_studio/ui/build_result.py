"""Result dialog shown after a build."""
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


def launch_game(launcher, directory):
    launcher = Path(launcher)
    if launcher.suffix.lower() == ".py":
        command = [sys.executable, str(launcher)]
    elif launcher.suffix.lower() == ".sh":
        command = ["sh", str(launcher)]
    else:
        command = [str(launcher)]
    subprocess.Popen(command, cwd=str(directory))


class BuildResultDialog(QDialog):
    def __init__(self, parent, result, translator):
        super().__init__(parent)
        self.t = translator
        self.result = result
        self.setWindowTitle(self.t("build.ready"))
        self.setMinimumWidth(620)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(self.t("build.path",
                                       path=result["path"])))
        warnings = result.get("warnings", [])
        if warnings:
            label = QLabel(self.t("build.warnings", count=len(warnings)))
            label.setObjectName("muted")
            label.setWordWrap(True)
            layout.addWidget(label)

        buttons = QHBoxLayout()
        open_button = QPushButton(self.t("build.open_folder"))
        open_button.clicked.connect(self.open_folder)
        buttons.addWidget(open_button)
        self.play_button = QPushButton(self.t("build.play"))
        self.play_button.setObjectName("primary")
        self.play_button.setEnabled(bool(result.get("launcher")))
        self.play_button.clicked.connect(self.play)
        buttons.addWidget(self.play_button)
        close_button = QPushButton(self.t("build.close"))
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def open_folder(self):
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.result["path"])))

    def play(self):
        launcher = self.result.get("launcher")
        if not launcher:
            QMessageBox.warning(self, self.t("build.ready"),
                                self.t("build.no_launcher"))
            return
        try:
            launch_game(launcher, self.result["path"])
        except OSError as exc:
            QMessageBox.critical(self, self.t("common.error"), str(exc))
