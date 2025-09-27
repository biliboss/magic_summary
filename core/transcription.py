"""Transcription service using OpenAI Whisper API."""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Callable, Tuple, TYPE_CHECKING

import subprocess

from openai import OpenAI

if TYPE_CHECKING:
    from faster_whisper import WhisperModel  # type: ignore import

from .config import get_openai_settings, get_ffmpeg_path
from .models import TranscriptSegment, ProcessingStatus

StatusCallback = Callable[[ProcessingStatus], None]


class TranscriptionService:
    def __init__(self, client: OpenAI | None = None):
        settings = get_openai_settings()
        self._settings = settings
        self._backend = settings.transcription_backend

        self._openai_client: OpenAI | None = None
        self._openai_model: str | None = None
        self._local_model = None

        if self._backend == "openai":
            self._openai_client = client or OpenAI(api_key=settings.api_key)
            self._openai_model = settings.model_transcription
        elif self._backend == "local":
            try:
                from faster_whisper import WhisperModel  # type: ignore import
            except ImportError as exc:  # pragma: no cover - import error path
                raise RuntimeError(
                    "faster-whisper não está instalado. Execute 'uv pip install faster-whisper'."
                ) from exc

            download_kwargs = {}
            if settings.local_download_root:
                download_kwargs["download_root"] = settings.local_download_root

            # Inicialização com fallback robusto para CPU
            self._local_model = self._load_local_model(settings.local_model_name, download_kwargs)
        else:
            raise ValueError(f"Transcription backend '{self._backend}' não é suportado")

    def _load_local_model(self, model_name: str, download_kwargs: dict) -> WhisperModel:
        """Carrega o modelo Whisper com fallback para CPU em caso de erro de GPU."""
        from faster_whisper import WhisperModel  # type: ignore import

        device = self._settings.local_device
        compute_type = self._settings.local_compute_type

        try:
            return WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                **download_kwargs,
            )
        except Exception as exc:
            error_str = str(exc).lower()
            if any(keyword in error_str for keyword in ["cudnn", "cuda", "invalid handle", "locate"]):
                print("Aviso: Erro de GPU (cuDNN/CUDA) detectado durante carregamento. Fazendo fallback para CPU.")
                return WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="float32",
                    **download_kwargs,
                )
            else:
                raise RuntimeError(f"Erro ao carregar modelo local: {exc}") from exc

    def transcribe(self, video_path: Path, status_cb: StatusCallback | None = None) -> list[TranscriptSegment]:
        if not video_path.exists():
            raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.05, message="Extraindo áudio"))

        audio_input, temp_path = self._prepare_audio(video_path)

        try:
            if self._backend == "openai":
                segments = self._transcribe_openai(audio_input, status_cb)
            else:
                # Para processamento local, fechamos o handle antes de reutilizar o arquivo.
                audio_input.close()
                segments = self._transcribe_local(temp_path, status_cb)
        finally:
            if not audio_input.closed:
                audio_input.close()
            temp_path.unlink(missing_ok=True)

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=1.0, message="Transcrição concluída"))

        return segments

    def _prepare_audio(self, video_path: Path) -> Tuple[BinaryIO, Path]:
        """Extract the audio track as a temporary WAV file and return an open handle and its path."""

        ffmpeg_bin = get_ffmpeg_path()
        temp_file = NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Extract audio track as WAV (16-bit PCM) which Whisper accepts.
        cmd = [
            str(ffmpeg_bin),
            "-y",
            "-i",
            str(video_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(temp_path),
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError("Falha ao extrair áudio com ffmpeg") from exc

        audio_handle = temp_path.open("rb")
        return audio_handle, temp_path

    # Backends -------------------------------------------------
    def _transcribe_openai(
        self,
        audio_input: BinaryIO,
        status_cb: StatusCallback | None = None,
    ) -> list[TranscriptSegment]:
        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.3, message="Enviando áudio para Whisper"))

        assert self._openai_client is not None
        assert self._openai_model is not None

        response = self._openai_client.audio.transcriptions.create(
            model=self._openai_model,
            file=audio_input,
            response_format="verbose_json",
            temperature=0.0,
        )

        segments = [
            TranscriptSegment(start=seg.start, end=seg.end, text=seg.text)
            for seg in response.segments
        ]
        return segments

    def _transcribe_local(
        self,
        audio_path: Path,
        status_cb: StatusCallback | None = None,
    ) -> list[TranscriptSegment]:
        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.3, message="Transcrevendo localmente"))

        assert self._local_model is not None

        try:
            segments_iter, info = self._local_model.transcribe(
                str(audio_path),
                beam_size=5,
                temperature=0.0,
            )

            duration = getattr(info, "duration", None) or 0.0
            results: list[TranscriptSegment] = []

            for segment in segments_iter:
                results.append(
                    TranscriptSegment(start=segment.start, end=segment.end, text=segment.text)
                )
                if status_cb and duration > 0:
                    progress = 0.3 + min(segment.end / duration, 1.0) * 0.6
                    status_cb(
                        ProcessingStatus(
                            status="transcribing",
                            progress=progress,
                            message="Transcrevendo localmente",
                        )
                    )

            if status_cb and not results:
                status_cb(
                    ProcessingStatus(
                        status="transcribing",
                        progress=0.9,
                        message="Transcrição local finalizando",
                    )
                )

            return results
        except Exception as exc:
            error_str = str(exc).lower()
            if any(keyword in error_str for keyword in ["cudnn", "cuda", "invalid handle", "locate"]):
                error_msg = "Erro de GPU (cuDNN/CUDA) durante transcrição. Reinicializando em CPU."
                if status_cb:
                    status_cb(ProcessingStatus(status="warning", progress=0.3, message=error_msg))
                # Re-inicializa o modelo em CPU e tenta novamente
                download_kwargs = {"download_root": self._settings.local_download_root} if self._settings.local_download_root else {}
                self._local_model = self._load_local_model(self._settings.local_model_name, download_kwargs)
                # Chama recursivamente com o novo modelo
                return self._transcribe_local(audio_path, status_cb)
            else:
                error_msg = f"Erro na transcrição local: {exc}"
                if status_cb:
                    status_cb(ProcessingStatus(status="error", progress=0.0, message=error_msg))
                raise RuntimeError(error_msg) from exc
