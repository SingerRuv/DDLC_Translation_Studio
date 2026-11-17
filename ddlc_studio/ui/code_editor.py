"""Read-only code preview with line numbers and Ren'Py highlighting."""
from pathlib import Path

from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class RenPyHighlighter(QSyntaxHighlighter):
    def __init__(self, document, dark=True):
        super().__init__(document)
        self.rules = []
        text = "#d4d4d4" if dark else "#1f1f1f"
        comment = "#6a9955" if dark else "#008000"
        string = "#ce9178" if dark else "#a31515"
        keyword = "#569cd6" if dark else "#0000ff"
        control = "#c586c0" if dark else "#af00db"
        number = "#b5cea8" if dark else "#098658"
        tag = "#d7ba7d" if dark else "#b8860b"
        self._base = QColor(text)

        def fmt(color, bold=False, italic=False):
            value = QTextCharFormat()
            value.setForeground(QColor(color))
            if bold:
                value.setFontWeight(QFont.Bold)
            if italic:
                value.setFontItalic(True)
            return value

        self.rules.extend([
            (QRegularExpression(r"#.*$"), fmt(comment, italic=True)),
            (QRegularExpression(r'"(?:\\.|[^"\\])*"'), fmt(string)),
            (QRegularExpression(r"'(?:\\.|[^'\\])*'"), fmt(string)),
            (QRegularExpression(r"\{[^}]+\}"), fmt(tag)),
            (QRegularExpression(
                r"\b(?:label|menu|screen|init|define|default|image|"
                r"transform|style|scene|show|hide|play|stop|voice|call|"
                r"jump|return|python|pass|if|elif|else|while|for|in|"
                r"with|at|as|use|expression)\b"), fmt(keyword, bold=True)),
            (QRegularExpression(r"\b(?:True|False|None|and|or|not)\b"),
             fmt(control)),
            (QRegularExpression(r"\b\d+(?:\.\d+)?\b"), fmt(number)),
        ])

    def highlightBlock(self, text):
        self.setFormat(0, len(text), self._base)
        for expression, value in self.rules:
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(),
                               value)


class CodePreview(QPlainTextEdit):
    def __init__(self, dark=True, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setObjectName("codeEditor")
        self.dark = dark
        self.setFont(QFont("Consolas", 10))
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._update_current_line)
        self._line_selection = QTextEdit.ExtraSelection()
        self.highlighter = RenPyHighlighter(self.document(), dark=dark)
        self._update_line_number_width()
        self._update_current_line()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _count=0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(contents.left(), contents.top(),
                  self.line_number_area_width(), contents.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(
            event.rect(), QColor("#1e1e1e" if self.dark else "#ffffff"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block)
                    .translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        color = QColor("#858585" if self.dark else "#999999")
        painter.setPen(color)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, top, self.line_number_area.width() - 6,
                    self.fontMetrics().height(), Qt.AlignRight,
                    str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def _update_current_line(self):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(
            QColor("#2a2d2e" if self.dark else "#e4e6f1"))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self._line_selection = selection
        self.setExtraSelections([selection])

    def load_file(self, path):
        try:
            text = Path(path).read_text(encoding="utf-8-sig",
                                        errors="replace")
        except OSError:
            text = ""
        self.setPlainText(text)
        self.moveCursor(QTextCursor.Start)

    def highlight_line(self, line_number):
        block = self.document().findBlockByNumber(max(0, line_number - 1))
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(
            QColor("#264f78" if self.dark else "#add6ff"))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = cursor
        self.setExtraSelections([selection])
        self.setTextCursor(cursor)
        self.centerCursor()

