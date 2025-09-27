"""PySide6 main window skeleton for Magic Summary."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import sys

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.models import ProcessingStatus, TopicSummary, VideoSummary


class MainWindow(QMainWindow):
    request_transcription = Signal(Path)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Feedback Summarizer")
        self.resize(1200, 720)
        self._create_actions()
        self._create_toolbar()
        self._create_content()

    def _create_actions(self) -> None:
        self.action_import = QAction("Importar vídeo", self)
        self.action_import.triggered.connect(self.open_file_dialog)

        self.action_quit = QAction("Sair", self)
        self.action_quit.triggered.connect(QApplication.quit)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self.action_import)
        toolbar.addSeparator()
        toolbar.addAction(self.action_quit)
        self.addToolBar(toolbar)

    def _create_content(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        self.label_status = QLabel("Arraste um vídeo ou importe para começar")
        self.label_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.button_import = QPushButton("Importar vídeo")
        self.button_import.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.button_import, alignment=Qt.AlignCenter)

        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter, stretch=1)

        # Player placeholder (left column)
        self.player_placeholder = QTextEdit()
        self.player_placeholder.setReadOnly(True)
        self.player_placeholder.setText("[PLAYER DE VÍDEO]\n(placeholder)")
        self.splitter.addWidget(self.player_placeholder)

        # Topics list (middle column)
        self.topic_list = QListWidget()
        self.topic_list.itemClicked.connect(self._on_topic_clicked)
        self.splitter.addWidget(self.topic_list)

        # Summary & transcript (right column)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        right_layout.addWidget(self.summary_box)

        self.transcript_box = QTextEdit()
        self.transcript_box.setReadOnly(True)
        right_layout.addWidget(self.transcript_box)

        self.splitter.addWidget(right_panel)
        self.setCentralWidget(container)

    # Public API -------------------------------------------------
    @Slot(Path)
    def open_file_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione um vídeo",
            "",
            "Vídeos (*.mp4 *.mkv *.mov)",
        )
        if file_path:
            self.request_transcription.emit(Path(file_path))

    def set_processing(self, status: ProcessingStatus) -> None:
        self.progress.setVisible(True)
        self.progress.setValue(int(status.progress * 100))
        self.label_status.setText(status.message or status.status)

    def set_ready(self) -> None:
        self.progress.setVisible(False)
        self.label_status.setText("Processamento concluído")

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Erro", message)
        self.progress.setVisible(False)
        self.label_status.setText("Não foi possível processar o vídeo")

    def display_summary(self, summary: VideoSummary) -> None:
        self.topic_list.clear()
        self.summary_box.clear()
        self.transcript_box.clear()

        if not summary.topics:
            self.summary_box.setPlainText("Nenhum tópico identificado")
            return

        for topic in summary.topics:
            item = QListWidgetItem(f"{topic.title} ({topic.timestamp})")
            self.topic_list.addItem(item)
            item.setData(Qt.UserRole, topic)

        self.summary_box.setPlainText("\n\n".join(
            f"# {topic.title}\n{topic.description}" for topic in summary.topics
        ))

        highlights_text = []
        for topic in summary.topics:
            for highlight in topic.highlights:
                highlights_text.append(
                    f"[{highlight.timestamp}] {highlight.title}: \"{highlight.quote}\""
                )
        if highlights_text:
            self.transcript_box.setPlainText("\n".join(highlights_text))

    # Slots -----------------------------------------------------
    def _on_topic_clicked(self, item: QListWidgetItem) -> None:
        topic: TopicSummary = item.data(Qt.UserRole)
        # TODO: Integrate with VLC player seek
        self.statusBar().showMessage(f"Jump to {topic.timestamp}")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
