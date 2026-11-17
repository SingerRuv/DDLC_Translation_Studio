"""Background project preparation."""
from PySide6.QtCore import QThread, Signal

from ..core.projects import create_project


class ProjectThread(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, base_path, source_path, settings=None, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.source_path = source_path
        self.settings = dict(settings or {})

    def run(self):
        try:
            summary = create_project(
                self.base_path, self.source_path, settings=self.settings,
                log=self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished_ok.emit(summary)
