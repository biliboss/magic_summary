"""Qt controller wiring transcription and summarization services to the UI."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal, Slot

from core.models import ProcessingStatus, VideoSummary, TranscriptSegment
from core.summarization import SummarizationService
from core.transcription import TranscriptionService
from core.storage import load_transcript, save_transcript, transcript_to_text

if TYPE_CHECKING:  # pragma: no cover
    from .main_window import MainWindow

logger = logging.getLogger(__name__)


class ProcessingWorker(QObject):
    """Background worker that runs transcription and summarization."""

    status = Signal(object)
    summary_ready = Signal(object)
    segments_ready = Signal(object)
    transcript_text_ready = Signal(str)
    backend_info_ready = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        video_path: Path,
        transcription_service: TranscriptionService,
        summarization_service: SummarizationService,
        cached_segments: list[TranscriptSegment] | None = None,
    ) -> None:
        super().__init__()
        self._video_path = Path(video_path)
        self._transcription_service = transcription_service
        self._summarization_service = summarization_service
        self._cached_segments = cached_segments

    def _on_status(self, status: ProcessingStatus) -> None:
        self.status.emit(status)

    @Slot()
    def run(self) -> None:
        try:
            if self._cached_segments is not None:
                segments = self._cached_segments
                self._on_status(
                    ProcessingStatus(
                        status="transcribing",
                        progress=0.4,
                        message="Transcrição carregada do cache",
                    )
                )
            else:
                segments = self._transcription_service.transcribe(
                    self._video_path,
                    status_cb=self._on_status,
                )
                try:
                    save_transcript(self._video_path, segments)
                except Exception as exc:  # pragma: no cover - best effort cache write
                    logger.warning("Não foi possível salvar cache da transcrição: %s", exc)

            self.segments_ready.emit(segments)
            self.transcript_text_ready.emit(transcript_to_text(segments))
            backend_info = self._transcription_service.get_backend_metadata()
            self.backend_info_ready.emit(backend_info)

            self._on_status(
                ProcessingStatus(
                    status="summarizing",
                    progress=0.9,
                    message="Gerando highlights",
                )
            )
            summary = self._summarization_service.summarize(segments)
            self._on_status(
                ProcessingStatus(
                    status="complete",
                    progress=1.0,
                    message="Resumo concluído",
                )
            )
            self.summary_ready.emit(summary)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Erro no processamento do vídeo: %s", exc)
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


class ProcessingController(QObject):
    """Coordinates user actions with the domain services."""

    def __init__(
        self,
        window: "MainWindow",
        transcription_service: Optional[TranscriptionService] = None,
        summarization_service: Optional[SummarizationService] = None,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._transcription = transcription_service or TranscriptionService()
        self._summarizer = summarization_service or SummarizationService()
        self._thread: Optional[QThread] = None
        self._worker: Optional[ProcessingWorker] = None

        self._window.request_transcription.connect(self.process_video)

    @Slot(Path)
    def process_video(self, video_path: Path) -> None:
        if self._thread and self._thread.isRunning():
            self._window.show_error("Já existe um processamento em andamento.")
            return

        video_path = Path(video_path)
        if not video_path.exists():
            self._window.show_error(f"Arquivo não encontrado: {video_path}")
            return

        cached_segments = load_transcript(video_path)
        cached_text = transcript_to_text(cached_segments) if cached_segments else None

        self._window.reset_results()
        self._window.set_busy(True)
        self._window.set_file_info(video_path)

        if cached_segments:
            self._window.set_processing(
                ProcessingStatus(
                    status="transcribing",
                    progress=0.3,
                    message="Transcrição carregada do cache",
                )
            )
            if cached_text:
                self._window.set_raw_transcript(cached_text)
        else:
            self._window.set_processing(
                ProcessingStatus(
                    status="preparing",
                    progress=0.05,
                    message=f"Preparando {video_path.name}",
                )
            )

        worker = ProcessingWorker(
            video_path,
            self._transcription,
            self._summarizer,
            cached_segments=cached_segments,
        )
        thread = QThread(parent=self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.status.connect(self._window.set_processing)
        worker.summary_ready.connect(self._on_summary_ready)
        worker.segments_ready.connect(self._on_segments_ready)
        worker.transcript_text_ready.connect(self._window.set_raw_transcript)
        worker.backend_info_ready.connect(self._window.set_backend_info)
        worker.error.connect(self._handle_error)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker

        logger.info("Iniciando processamento de %s", video_path)
        thread.start()

    def _on_summary_ready(self, summary: VideoSummary) -> None:
        self._window.display_summary(summary)
        self._window.set_ready()
        self._window.set_busy(False)
        self._window.statusBar().showMessage("Resumo gerado", 5000)

    def _handle_error(self, message: str) -> None:
        self._window.show_error(message)
        self._window.set_busy(False)

    def _on_finished(self) -> None:
        logger.info("Processamento finalizado")
        self._thread = None
        self._worker = None

    def _on_segments_ready(self, segments: list[TranscriptSegment]) -> None:
        self._window.cache_segments(segments)
