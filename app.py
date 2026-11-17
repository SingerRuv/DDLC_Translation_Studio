"""DDLC Translation Studio entry point."""
import sys

from PySide6.QtWidgets import QApplication

from ddlc_studio.config import APP, load_settings
from ddlc_studio.i18n import Translator
from ddlc_studio.ui.start_window import StartWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setOrganizationName("DDLC Translation Studio")
    app.setStyle("Fusion")
    settings = load_settings()
    translator = Translator(settings.get("language", "es"))
    window = StartWindow(settings, translator)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
