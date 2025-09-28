"""PySide6 main window skeleton for Magic Summary."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import sys

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtGui import QAction, QTextCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
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
    QFrame,
    QTabWidget,
    QToolBar,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.models import (
    ProcessingStatus,
    TopicSummary,
    TopicHighlight,
    VideoSummary,
    TranscriptSegment,
    SummaryMetadata,
)


class MainWindow(QMainWindow):
    request_transcription = Signal(Path)
    request_regeneration = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Feedback Summarizer")
        self.resize(1200, 720)
        self.statusBar()
        self._create_actions()
        self._create_toolbar()
        self._is_busy = False
        self._current_file: Optional[Path] = None
        self._segments: list[TranscriptSegment] | None = None
        self._current_summary: VideoSummary | None = None
        self._has_summary = False
        self._was_playing = False
        self._media_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.positionChanged.connect(self._on_position_changed)
        self._media_player.durationChanged.connect(self._on_duration_changed)
        self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._create_content()


    def _create_actions(self) -> None:
        self.action_import = QAction("Importar vídeo", self)
        self.action_import.triggered.connect(self.open_file_dialog)

        self.action_regenerate = QAction("Regerar resumo", self)
        self.action_regenerate.triggered.connect(self._on_regenerate_clicked)

        self.action_quit = QAction("Sair", self)
        self.action_quit.triggered.connect(QApplication.quit)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self.action_import)
        toolbar.addAction(self.action_regenerate)
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

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)

        self.backend_frame = QFrame()
        backend_layout = QHBoxLayout(self.backend_frame)
        backend_layout.setContentsMargins(0, 0, 0, 0)
        backend_layout.setSpacing(12)

        self.backend_label = QLabel()
        self.backend_label.setAlignment(Qt.AlignCenter)
        backend_layout.addWidget(self.backend_label, alignment=Qt.AlignCenter)

        self.backend_frame.setVisible(False)
        layout.addWidget(self.backend_frame)

        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter, stretch=1)

        # Player panel (left column)
        player_panel = QWidget()
        player_layout = QVBoxLayout(player_panel)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(6)

        self.video_widget = QVideoWidget()
        player_layout.addWidget(self.video_widget)
        self._media_player.setVideoOutput(self.video_widget)

        controls_layout = QHBoxLayout()
        self.button_play = QPushButton("Reproduzir")
        self.button_play.clicked.connect(self.toggle_playback)
        self.button_play.setEnabled(False)
        controls_layout.addWidget(self.button_play)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderPressed.connect(self._on_slider_pressed)
        self.position_slider.sliderReleased.connect(self._on_slider_released)
        self.position_slider.sliderMoved.connect(self._on_slider_moved)
        self.position_slider.setEnabled(False)
        controls_layout.addWidget(self.position_slider, stretch=1)

        player_layout.addLayout(controls_layout)
        self.splitter.addWidget(player_panel)

        # Topics list (middle column)
        self.topic_list = QListWidget()
        self.topic_list.itemClicked.connect(self._on_topic_clicked)
        self.topic_list.setMinimumWidth(220)
        self.topic_list.setMaximumWidth(360)
        self.splitter.addWidget(self.topic_list)

        # Summary & transcript (right column)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setMinimumWidth(360)

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        right_layout.addWidget(self.summary_box)

        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)

        self.highlights_list = QListWidget()
        self.highlights_list.itemClicked.connect(self._on_highlight_clicked)
        self.tabs.addTab(self.highlights_list, "Highlights")

        self.raw_transcript_box = QTextEdit()
        self.raw_transcript_box.setReadOnly(True)
        self.tabs.addTab(self.raw_transcript_box, "Transcrição")

        self.summary_meta_label = QLabel()
        self.summary_meta_label.setWordWrap(True)
        self.summary_meta_label.setVisible(False)
        right_layout.addWidget(self.summary_meta_label)

        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setStretchFactor(2, 3)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)
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

    @Slot()
    def _on_regenerate_clicked(self) -> None:
        if self._is_busy:
            self.statusBar().showMessage("Aguarde finalizar o processamento atual", 3000)
            return
        self.request_regeneration.emit()

    def set_processing(self, status: ProcessingStatus) -> None:
        self.progress.setVisible(True)
        self.progress.setValue(int(status.progress * 100))
        self.label_status.setText(status.message or status.status)

    def set_ready(self) -> None:
        self.progress.setVisible(False)
        self.label_status.setText("Processamento concluído")
        self._update_regenerate_state()

    def set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        self.button_import.setEnabled(not busy)
        self.action_import.setEnabled(not busy)
        self._update_regenerate_state()

    def reset_results(self) -> None:
        self.topic_list.clear()
        self.summary_box.clear()
        self.highlights_list.clear()
        self.raw_transcript_box.clear()
        self.info_label.clear()
        self.info_label.setVisible(False)
        self._segments = None
        self.backend_label.clear()
        self.backend_frame.setVisible(False)
        self.summary_meta_label.clear()
        self.summary_meta_label.setVisible(False)
        self.position_slider.setValue(0)
        self.position_slider.setRange(0, 0)
        self.button_play.setText("Reproduzir")
        self._has_summary = False
        self._was_playing = False
        self._media_player.stop()
        self._media_player.setSource(QUrl())
        self._update_regenerate_state()
        self.button_play.setEnabled(False)
        self.position_slider.setEnabled(False)
        self._current_summary = None

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Erro", message)
        self.progress.setVisible(False)
        self.label_status.setText("Não foi possível processar o vídeo")
        self.statusBar().clearMessage()

    def display_summary(self, summary: VideoSummary) -> None:
        self.topic_list.clear()
        self.summary_box.clear()
        self.highlights_list.clear()
        self._current_summary = summary

        if not summary.topics:
            self.summary_box.setPlainText("Nenhum tópico identificado")
            self._has_summary = False
            self._update_regenerate_state()
            return

        for topic in summary.topics:
            item = QListWidgetItem(f"{topic.title} ({topic.timestamp})")
            item.setData(Qt.UserRole, topic)
            self.topic_list.addItem(item)

        self._populate_transcript(summary)
        self.tabs.setCurrentWidget(self.highlights_list)
        self._has_summary = True
        self._update_regenerate_state()

        self.topic_list.setCurrentRow(0)
        first_topic_item = self.topic_list.item(0)
        if first_topic_item:
            self._show_topic_details(first_topic_item.data(Qt.UserRole))
        else:
            self.summary_box.setPlainText("Selecione um tópico para ver os detalhes")

    def _on_topic_clicked(self, item: QListWidgetItem) -> None:
        topic: TopicSummary = item.data(Qt.UserRole)
        self._seek_to_timestamp(topic.timestamp)
        self.statusBar().showMessage(f"Pulando para {topic.timestamp}")
        self._show_topic_details(topic)

    def set_file_info(self, file_path: Path, duration: float | None = None) -> None:
        self._current_file = file_path
        parts = [file_path.name]
        if duration is not None:
            minutes, seconds = divmod(int(duration), 60)
            parts.append(f"duração {minutes:02d}:{seconds:02d}")
        self.info_label.setText(" • ".join(parts))
        self.info_label.setVisible(True)
        self._media_player.setSource(QUrl.fromLocalFile(str(file_path)))
        self.position_slider.setValue(0)
        self.position_slider.setRange(0, 0)
        self.position_slider.setEnabled(False)
        self.button_play.setEnabled(True)
        self._was_playing = False

    def _populate_transcript(self, summary: VideoSummary) -> None:
        self.highlights_list.clear()
        for topic in summary.topics:
            for highlight in topic.highlights:
                item = QListWidgetItem(
                    f"[{highlight.timestamp}] {highlight.title}\n{highlight.quote}"
                )
                item.setData(Qt.UserRole, highlight)
                self.highlights_list.addItem(item)

    def set_raw_transcript(self, text: str) -> None:
        self.raw_transcript_box.setPlainText(text)

    def cache_segments(self, segments: list[TranscriptSegment]) -> None:
        self._segments = segments
        if segments:
            duration = segments[-1].end
            self.position_slider.setRange(0, int(duration * 1000))
            self.position_slider.setEnabled(True)
        else:
            self.position_slider.setEnabled(False)

    def set_backend_info(self, info: dict) -> None:
        backend = info.get("backend", "?")
        if backend == "openai":
            model = info.get("model") or "-"
            self.backend_label.setText(f"Backend: OpenAI • Modelo: {model}")
        else:
            engine = info.get("engine", "local")
            model = info.get("model") or "-"
            device = info.get("device") or "?"
            compute = info.get("compute") or "?"
            self.backend_label.setText(
                f"Backend: {engine} ({backend}) • Modelo: {model} • Dispositivo: {device} • Precisão: {compute}"
            )
        self.backend_frame.setVisible(True)

    def set_summary_metadata(self, metadata: SummaryMetadata) -> None:
        parts = []
        if metadata.prompt_version:
            parts.append(f"Prompt v{metadata.prompt_version}")
        if metadata.regenerated_at:
            try:
                ts = datetime.fromisoformat(metadata.regenerated_at)
                parts.append(f"Gerado em {ts.astimezone().strftime('%d/%m/%Y %H:%M:%S')}")
            except ValueError:
                parts.append(f"Gerado em {metadata.regenerated_at}")
        if metadata.backend_model:
            parts.append(f"Modelo resumo: {metadata.backend_model}")
        backend_info = metadata.extra.get("transcription_backend") if metadata.extra else None
        if isinstance(backend_info, dict):
            backend_desc = backend_info.get("device") or backend_info.get("backend")
            if backend_desc:
                parts.append(f"Transcrição: {backend_desc}")
        if not parts:
            self.summary_meta_label.setVisible(False)
            return
        self.summary_meta_label.setText(" • ".join(parts))
        self.summary_meta_label.setVisible(True)

    # Media controls -------------------------------------------
    @Slot()
    def toggle_playback(self) -> None:
        if self._media_player.source().isEmpty():
            if not self._current_file:
                self.statusBar().showMessage("Nenhum vídeo carregado", 3000)
                return
            self._media_player.setSource(QUrl.fromLocalFile(str(self._current_file)))
        if self._media_player.playbackState() == QMediaPlayer.PlayingState:
            self._media_player.pause()
        else:
            self._media_player.play()

    def _topic_row(self, topic: TopicSummary) -> int | None:
        for index in range(self.topic_list.count()):
            item = self.topic_list.item(index)
            stored = item.data(Qt.UserRole)
            if stored is topic:
                return index
        return None

    def _show_topic_details(
        self,
        topic: TopicSummary,
        selected_highlight: TopicHighlight | None = None,
    ) -> None:
        lines: list[str] = []
        lines.append(f"{topic.title} ({topic.timestamp})")
        if topic.description:
            lines.extend(["", topic.description.strip()])

        if topic.highlights:
            lines.append("")
            lines.append("Highlights:")
            for highlight in topic.highlights:
                prefix = "→" if highlight is selected_highlight else "-"
                quote = highlight.quote.strip()
                lines.append(
                    f"{prefix} [{highlight.timestamp}] {highlight.title}: \"{quote}\""
                )
        self.summary_box.setPlainText("\n".join(lines))

    def _find_topic_for_highlight(self, highlight: TopicHighlight) -> TopicSummary | None:
        if not self._current_summary:
            return None
        for topic in self._current_summary.topics:
            for candidate in topic.highlights:
                if (
                    candidate.timestamp == highlight.timestamp
                    and candidate.title == highlight.title
                    and candidate.quote == highlight.quote
                ):
                    return topic
        return None

    def _on_position_changed(self, position: int) -> None:
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)

    def _on_duration_changed(self, duration: int) -> None:
        if duration <= 0:
            return
        self.position_slider.setRange(0, duration)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlayingState:
            self.button_play.setText("Pausar")
        else:
            self.button_play.setText("Reproduzir")

    def _on_slider_pressed(self) -> None:
        self._was_playing = self._media_player.playbackState() == QMediaPlayer.PlayingState
        self._media_player.pause()

    def _on_slider_released(self) -> None:
        self._media_player.setPosition(self.position_slider.value())
        if self._was_playing:
            self._media_player.play()
        self._was_playing = False

    def _on_slider_moved(self, position: int) -> None:
        self._media_player.setPosition(position)

    def _on_highlight_clicked(self, item: QListWidgetItem) -> None:
        highlight = item.data(Qt.UserRole)
        if highlight is None:
            return
        self._seek_to_timestamp(highlight.timestamp)
        self.statusBar().showMessage(f"Pulando para {highlight.timestamp}")
        topic = self._find_topic_for_highlight(highlight)
        if topic:
            row = self._topic_row(topic)
            if row is not None:
                self.topic_list.blockSignals(True)
                self.topic_list.setCurrentRow(row)
                self.topic_list.blockSignals(False)
            self._show_topic_details(topic, highlight)

    def _seek_to_timestamp(self, timestamp: str) -> None:
        try:
            minutes, seconds = timestamp.split(":")
            total_seconds = int(minutes) * 60 + int(seconds)
        except ValueError:
            return
        self._media_player.setPosition(total_seconds * 1000)
        if self._media_player.playbackState() != QMediaPlayer.PlayingState:
            self._media_player.play()
        self.button_play.setText("Pausar")

    def _update_regenerate_state(self) -> None:
        self.action_regenerate.setEnabled(self._has_summary and not self._is_busy)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
