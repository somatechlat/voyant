"""
Voyant Scraper - Audio/Video Transcription

Transcription of audio and video files using SpeechRecognition and Whisper.
"""
from typing import Optional, Dict, Any
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class TranscriptionProcessor:
    """
    Transcription processor for audio and video files.
    
    Engines:
    - speech_recognition: Google/CMU Sphinx
    - whisper: OpenAI Whisper (local or API)
    """
    
    def __init__(
        self,
        engine: str = "whisper",
        whisper_model: str = "base",
        language: str = "es"
    ):
        self.engine = engine
        self.whisper_model = whisper_model
        self.language = language
        self._whisper = None
    
    def _get_whisper(self):
        """Lazy load Whisper model."""
        if self._whisper is None:
            import whisper
            self._whisper = whisper.load_model(self.whisper_model)
        return self._whisper
    
    def extract_audio_from_video(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        Extract audio track from video file.
        
        Args:
            video_path: Path to video file
            output_path: Optional output path for audio
            
        Returns:
            Path to extracted audio file (WAV)
        """
        import ffmpeg
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")
        
        ffmpeg.input(video_path).output(
            output_path,
            acodec='pcm_s16le',
            ac=1,
            ar='16000'
        ).overwrite_output().run(quiet=True)
        
        return output_path
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with text, segments, language, duration
        """
        if self.engine == "whisper":
            return self._transcribe_whisper(audio_path)
        else:
            return self._transcribe_speech_recognition(audio_path)
    
    def transcribe_video(self, video_path: str) -> Dict[str, Any]:
        """
        Transcribe video file by extracting audio first.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with transcription result
        """
        audio_path = None
        try:
            audio_path = self.extract_audio_from_video(video_path)
            result = self.transcribe_audio(audio_path)
            result["source_type"] = "video"
            return result
        finally:
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
    
    def _transcribe_whisper(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper."""
        model = self._get_whisper()
        
        result = model.transcribe(
            audio_path,
            language=self.language,
            fp16=False
        )
        
        segments = [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            }
            for seg in result.get("segments", [])
        ]
        
        return {
            "text": result["text"],
            "language": result.get("language", self.language),
            "segments": segments,
            "engine": f"whisper-{self.whisper_model}",
            "source_type": "audio"
        }
    
    def _transcribe_speech_recognition(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using SpeechRecognition library."""
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        
        try:
            # Try Google Speech Recognition first
            text = recognizer.recognize_google(audio, language=self.language)
            engine = "google"
        except sr.UnknownValueError:
            text = ""
            engine = "google-failed"
        except sr.RequestError:
            # Fallback to CMU Sphinx (offline)
            try:
                text = recognizer.recognize_sphinx(audio)
                engine = "sphinx"
            except Exception:
                text = ""
                engine = "sphinx-failed"
        
        return {
            "text": text,
            "language": self.language,
            "segments": [],
            "engine": engine,
            "source_type": "audio"
        }
    
    def transcribe_bytes(
        self, 
        audio_bytes: bytes, 
        format: str = "wav",
        is_video: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe from bytes.
        
        Args:
            audio_bytes: Audio/video file bytes
            format: File format
            is_video: Whether this is a video file
            
        Returns:
            Transcription result
        """
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            if is_video:
                return self.transcribe_video(temp_path)
            return self.transcribe_audio(temp_path)
        finally:
            os.unlink(temp_path)
