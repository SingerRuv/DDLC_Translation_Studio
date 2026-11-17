"""Background build thread."""
from PySide6.QtCore import QThread, Signal

from ..core.build import build_project


class BuildThread(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, project_path, settings, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.settings = dict(settings)

    def run(self):
        try:
            result = build_project(
                self.project_path, self.settings, log=self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished_ok.emit(result)
