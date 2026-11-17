"""Three-step project creation wizard."""
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..core.modinfo import validate_base, validate_source
from ..core.projects import project_path_for


class BasePage(QWizardPage):
    def __init__(self, translator, settings):
        super().__init__()
        self.t = translator
        self.settings = settings
        self.setTitle(self.t("wizard.base_title"))
        layout = QVBoxLayout(self)
        description = QLabel(self.t("wizard.base_desc"))
        description.setWordWrap(True)
        layout.addWidget(description)
        row = QHBoxLayout()
        self.path = QLineEdit(settings.get("last_base", ""))
        self.path.setPlaceholderText(
            r"C:\Users\you\Desktop\DDLC-1.1.1-pc")
        browse = QPushButton(self.t("wizard.browse"))
        browse.clicked.connect(self._browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        layout.addStretch(1)

    def _browse(self):
        start = self.path.text().strip() or str(Path.home() / "Desktop")
        path = QFileDialog.getExistingDirectory(
            self, self.t("wizard.base_title"), start)
        if path:
            self.path.setText(path)

    def validatePage(self):
        try:
            validate_base(self.path.text().strip())
        except Exception as exc:
            QMessageBox.warning(self, self.t("wizard.base_title"), str(exc))
            return False
        return True


class SourcePage(QWizardPage):
    def __init__(self, translator):
        super().__init__()
        self.t = translator
        self.setTitle(self.t("wizard.source_title"))
        self.version = ""
        self.kind = ""
        layout = QVBoxLayout(self)
        description = QLabel(self.t("wizard.source_desc"))
        description.setWordWrap(True)
        layout.addWidget(description)
        row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText(r"C:\path\to\renpy-source-project")
        browse = QPushButton(self.t("wizard.browse"))
        browse.clicked.connect(self._browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        self.version_label = QLabel("")
        self.version_label.setObjectName("muted")
        layout.addWidget(self.version_label)
        layout.addStretch(1)

    def _browse(self):
        start = self.path.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self, self.t("wizard.source_title"), start)
        if path:
            self.path.setText(path)

    def validatePage(self):
        try:
            _root, self.version, self.kind = validate_source(
                self.path.text().strip())
        except Exception as exc:
            QMessageBox.warning(self, self.t("wizard.source_title"),
                                str(exc))
            return False
        if self.kind == "overlay":
            self.version_label.setText(self.t("wizard.overlay"))
        else:
            self.version_label.setText(
                "%s: %s" % (self.t("wizard.version"), self.version))
        return True


class ReviewPage(QWizardPage):
    def __init__(self, wizard, translator):
        super().__init__()
        self.wizard = wizard
        self.t = translator
        self.setTitle(self.t("wizard.review_title"))
        layout = QVBoxLayout(self)
        self.base = QLabel()
        self.source = QLabel()
        self.version = QLabel()
        self.project = QLabel()
        self.note = QLabel()
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        for label in (self.base, self.source, self.version, self.project):
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addWidget(self.note)
        layout.addStretch(1)

    def initializePage(self):
        base = self.wizard.base_page.path.text().strip()
        source = self.wizard.source_page.path.text().strip()
        self.base.setText("%s: %s" % (self.t("wizard.base"), base))
        self.source.setText("%s: %s" % (self.t("wizard.source"), source))
        if self.wizard.source_page.kind == "overlay":
            self.version.setText(self.t("wizard.overlay"))
        else:
            self.version.setText("%s: %s" % (
                self.t("wizard.version"), self.wizard.source_page.version))
        project = project_path_for(Path(source)) if source else Path()
        self.project.setText("%s: %s" % (self.t("wizard.project"), project))
        exists = (project / "project.sqlite3").is_file()
        self.note.setText(self.t("wizard.existing") if exists else "")


class NewProjectWizard(QWizard):
    def __init__(self, parent, translator, settings):
        super().__init__(parent)
        self.t = translator
        self.settings = settings
        self.setWindowTitle(self.t("wizard.title"))
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.resize(760, 480)
        self.base_page = BasePage(translator, settings)
        self.source_page = SourcePage(translator)
        self.review_page = ReviewPage(self, translator)
        self.addPage(self.base_page)
        self.addPage(self.source_page)
        self.addPage(self.review_page)
        self.setButtonText(QWizard.NextButton, self.t("wizard.next"))
        self.setButtonText(QWizard.BackButton, self.t("wizard.back"))
        self.setButtonText(QWizard.FinishButton, self.t("wizard.finish"))
        self.setButtonText(QWizard.CancelButton, self.t("wizard.cancel"))

    @property
    def base_path(self):
        return self.base_page.path.text().strip()

    @property
    def source_path(self):
        return self.source_page.path.text().strip()

