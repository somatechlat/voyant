"""
Voyant Scraper - Audio/Video Transcription for Multimedia Content.

This module provides functionalities for converting spoken language from
audio and video files into text. It integrates with various transcription
engines, including `SpeechRecognition` (supporting Google Speech Recognition,
CMU Sphinx, etc.) and `OpenAI Whisper` for highly accurate transcription.
"""

import logging
import os
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TranscriptionProcessor:
    """
    A processor for extracting text transcriptions from audio and video files.

    This class provides an abstraction over different transcription engines,
    allowing selection based on accuracy requirements, offline capabilities,
    and computational resources.

    Supported Engines:
    - `speech_recognition`: Utilizes various backend APIs (e.g., Google Web Speech API)
                            or offline engines (e.g., CMU Sphinx).
    - `whisper`: Leverages OpenAI's Whisper model for highly accurate,
                 local or cloud-based transcription.
    """

    def __init__(
        self, engine: str = "whisper", whisper_model: str = "base", language: str = "es"
    ):
        """
        Initializes the TranscriptionProcessor.

        Args:
            engine (str): The primary transcription engine to use ("whisper" or "speech_recognition").
            whisper_model (str): The Whisper model to load (e.g., "base", "small", "medium", "large").
                                 Applicable only if `engine` is "whisper".
            language (str): The language of the audio/video content (e.g., "en", "es").
        """
        self.engine = engine
        self.whisper_model = whisper_model
        self.language = language
        self._whisper = None  # Lazy-loaded Whisper model.

    def _get_whisper(self):
        """
        Lazily loads and returns the OpenAI Whisper model instance.

        Returns:
            whisper.model.Whisper: The loaded Whisper model.

        Raises:
            ImportError: If the `openai-whisper` package is not installed.
            Exception: If there's an issue loading the specified Whisper model.
        """
        if self._whisper is None:
            try:
                import whisper
                self._whisper = whisper.load_model(self.whisper_model)
            except ImportError:
                raise ImportError("The 'openai-whisper' package is not installed. Please install it to use Whisper engine.")
            except Exception as e:
                logger.error(f"Failed to load Whisper model '{self.whisper_model}': {e}")
                raise
        return self._whisper

    def extract_audio_from_video(
        self, video_path: str, output_path: Optional[str] = None
    ) -> str:
        """
        Extracts the audio track from a video file and saves it as a WAV file.

        Args:
            video_path (str): The file path to the input video file.
            output_path (Optional[str]): The desired file path for the extracted audio.
                                         If None, a temporary WAV file will be created.

        Returns:
            str: The file path to the extracted audio WAV file.

        Raises:
            ImportError: If the `ffmpeg-python` package is not installed or `ffmpeg` is not in PATH.
            ffmpeg.Error: If `ffmpeg` encounters an error during audio extraction.
        """
        import ffmpeg

        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")

        ffmpeg.input(video_path).output(
            output_path, acodec="pcm_s16le", ac=1, ar="16000"  # 16kHz mono audio.
        ).overwrite_output().run(quiet=True)  # `quiet=True` suppresses ffmpeg's console output.

        return output_path

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes an audio file to text using the configured transcription engine.

        Args:
            audio_path (str): The file path to the audio file.

        Returns:
            Dict[str, Any]: A dictionary containing the transcription result,
                            including the extracted text, language, and segments (if available).

        Raises:
            ImportError: If required packages for the selected engine are not installed.
            Exception: For any errors encountered during transcription.
        """
        if self.engine == "whisper":
            return self._transcribe_whisper(audio_path)
        else:
            return self._transcribe_speech_recognition(audio_path)

    def transcribe_video(self, video_path: str) -> Dict[str, Any]:
        """
        Transcribes a video file by first extracting its audio track, then transcribing the audio.

        Args:
            video_path (str): The file path to the video file.

        Returns:
            Dict[str, Any]: A dictionary containing the transcription result,
                            including the extracted text and metadata, with `source_type` set to "video".

        Raises:
            ImportError: If required packages (e.g., `ffmpeg-python`) are not installed.
            Exception: For any errors encountered during audio extraction or transcription.
        """
        audio_path = None
        try:
            audio_path = self.extract_audio_from_video(video_path)
            result = self.transcribe_audio(audio_path)
            result["source_type"] = "video"
            return result
        finally:
            # Ensure the temporary audio file is deleted after transcription.
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)

    def _transcribe_whisper(self, audio_path: str) -> Dict[str, Any]:
        """
        Internal method: Transcribes audio using the OpenAI Whisper model.

        Args:
            audio_path (str): Path to the audio file.

        Returns:
            Dict[str, Any]: Transcription result, including text, language, and detailed segments.
        """
        model = self._get_whisper()

        # Whisper can automatically detect language, but providing it can improve accuracy.
        result = model.transcribe(audio_path, language=self.language, fp16=False)

        segments = [
            {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
            for seg in result.get("segments", [])
        ]

        return {
            "text": result["text"],
            "language": result.get("language", self.language),
            "segments": segments,
            "engine": f"whisper-{self.whisper_model}",
            "source_type": "audio",
        }

    def _transcribe_speech_recognition(self, audio_path: str) -> Dict[str, Any]:
        """
        Internal method: Transcribes audio using the `speech_recognition` library,
        attempting Google Speech Recognition with CMU Sphinx as a fallback.

        Args:
            audio_path (str): Path to the audio file.

        Returns:
            Dict[str, Any]: Transcription result, including text, language, and engine used.
        """
        import speech_recognition as sr

        recognizer = sr.Recognizer()

        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        try:
            # Attempt Google Speech Recognition (online API).
            text = recognizer.recognize_google(audio, language=self.language)
            engine = "google"
        except sr.UnknownValueError:
            text = ""
            engine = "google-failed"
            logger.warning("Google Speech Recognition could not understand audio.")
        except sr.RequestError as e:
            text = ""
            engine = "google-request-failed"
            logger.warning(f"Could not request results from Google Speech Recognition service; {e}")
            # Fallback to CMU Sphinx (offline engine) if Google API fails.
            try:
                text = recognizer.recognize_sphinx(audio, language=self.language) # Sphinx language codes may differ.
                engine = "sphinx"
                logger.info("Successfully used CMU Sphinx as fallback.")
            except Exception as e_sphinx:
                text = ""
                engine = "sphinx-failed"
                logger.error(f"CMU Sphinx Recognition failed; {e_sphinx}")
        except Exception as e:
            text = ""
            engine = "speech_recognition-failed"
            logger.error(f"An unexpected error occurred during SpeechRecognition: {e}")

        return {
            "text": text,
            "language": self.language,
            "segments": [],  # SpeechRecognition generally doesn't provide fine-grained segments.
            "engine": engine,
            "source_type": "audio",
        }

    def transcribe_bytes(
        self, audio_bytes: bytes, format: str = "wav", is_video: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribes audio or video content provided as raw bytes.

        This method saves the bytes to a temporary file, processes it, and then
        cleans up the temporary file.

        Args:
            audio_bytes (bytes): The raw bytes content of the audio or video file.
            format (str, optional): The file format (e.g., "wav", "mp4"). Defaults to "wav".
            is_video (bool, optional): If True, the bytes are treated as a video file
                                       from which audio will be extracted. Defaults to False.

        Returns:
            Dict[str, Any]: The transcription result.

        Raises:
            Exception: For any errors encountered during temporary file handling or transcription.
        """
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            if is_video:
                return self.transcribe_video(temp_path)
            return self.transcribe_audio(temp_path)
        finally:
            # Ensure the temporary file is deleted after processing.
            os.unlink(temp_path)
