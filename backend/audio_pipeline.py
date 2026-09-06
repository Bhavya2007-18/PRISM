# ENGINE: VoiceEngine
"""
PRISM Audio Pipeline — Voice Engine Entry Point

Single canonical entry point for all audio processing:

    AudioCapture → VAD → TurnDetection → STT → TranscriptEvent

This module wires the VoiceEngine components together. It is the
authoritative pipeline for real audio; the Agora path handles its own
audio transport, but this pipeline is used for /asr and /ws/vad endpoints.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioPipelineConfig:
    """Configuration for the PRISM audio pipeline."""
    sample_rate: int = 16000
    chunk_size: int = 512              # samples per VAD chunk
    silence_threshold_ms: int = 480    # ms of silence to end a turn
    min_speech_ms: int = 150           # minimum speech duration to process
    max_utterance_ms: int = 15000      # maximum utterance before forced turn end
    noise_floor_calibration_ms: int = 500  # ms to calibrate noise floor on session start
    language: Optional[str] = None     # hint for STT (e.g. 'hi', 'en')


@dataclass
class TranscriptEvent:
    """Emitted when a transcript is available (partial or final)."""
    text: str
    is_final: bool
    language: Optional[str] = None
    confidence: float = 0.0
    timestamp: Optional[str] = None


class AudioPipeline:
    """
    Wires VAD + STT into a turn-based transcript pipeline.

    Usage:
        config = AudioPipelineConfig(language='hi')
        pipeline = AudioPipeline(config)
        pipeline.on_transcript = lambda event: ...  # callback
        pipeline.process_audio_chunk(pcm_bytes)
    """

    def __init__(self, config: Optional[AudioPipelineConfig] = None):
        self.config = config or AudioPipelineConfig()
        self.on_transcript: Optional[Callable[[TranscriptEvent], None]] = None
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[], None]] = None
        self.on_barge_in: Optional[Callable[[], None]] = None
        self._vad_processor = None
        self._speech_buffer: list = []
        self._is_initialized = False

    def initialize(self) -> bool:
        """Initialize VAD model. Returns True if ready."""
        try:
            from vad_service import get_vad_model, VADProcessor
            model = get_vad_model()
            if model is None:
                logger.warning("[AudioPipeline] VAD model unavailable — pipeline degraded")
                return False
            self._vad_processor = VADProcessor(
                model,
                silence_duration_ms=self.config.silence_threshold_ms,
                min_speech_duration_ms=self.config.min_speech_ms,
                max_utterance_duration_ms=self.config.max_utterance_ms,
            )
            self._is_initialized = True
            logger.info("[AudioPipeline] Initialized (VAD ready)")
            return True
        except Exception as e:
            logger.error(f"[AudioPipeline] Initialization failed: {e}")
            return False

    def process_audio_chunk(self, pcm_bytes: bytes) -> list:
        """
        Process a chunk of raw 16kHz 16-bit PCM audio.
        Returns list of events: speech_start, speech_end, barge_in, transcript, error.
        """
        if not self._is_initialized or self._vad_processor is None:
            return []

        events = self._vad_processor.process_chunk(pcm_bytes)
        results = []

        for event in events:
            event_type = event.get("event")
            if event_type == "speech_start":
                self._speech_buffer = [pcm_bytes]
                if self.on_speech_start:
                    self.on_speech_start()
                results.append(event)
            elif event_type == "speech_end":
                if self.on_speech_end:
                    self.on_speech_end()
                results.append(event)
                # Transcribe accumulated audio
                transcript_event = self._transcribe_buffer()
                if transcript_event and transcript_event.text:
                    results.append({
                        "event": "transcript",
                        "text": transcript_event.text,
                        "is_final": True,
                        "language": transcript_event.language,
                        "confidence": transcript_event.confidence,
                    })
                    if self.on_transcript:
                        self.on_transcript(transcript_event)
                self._speech_buffer = []
            elif event_type == "turn_complete":
                results.append(event)
            elif event_type == "barge_in":
                if self.on_barge_in:
                    self.on_barge_in()
                results.append(event)
            else:
                results.append(event)

            # Accumulate audio during speech
            if self._vad_processor.is_speaking:
                self._speech_buffer.append(pcm_bytes)

        return results

    def _transcribe_buffer(self) -> Optional[TranscriptEvent]:
        """Transcribe accumulated PCM audio buffer via Faster Whisper."""
        if not self._speech_buffer:
            return None
        try:
            import io
            import struct
            from asr_service import transcribe_audio

            # Combine PCM chunks into WAV bytes
            pcm_data = b"".join(self._speech_buffer)
            sample_rate = self.config.sample_rate
            num_channels = 1
            bits_per_sample = 16
            num_samples = len(pcm_data) // 2
            wav_header = struct.pack(
                '<4sI4s4sIHHIIHH4sI',
                b'RIFF', 36 + len(pcm_data), b'WAVE',
                b'fmt ', 16, 1, num_channels, sample_rate,
                sample_rate * num_channels * bits_per_sample // 8,
                num_channels * bits_per_sample // 8, bits_per_sample,
                b'data', len(pcm_data)
            )
            wav_bytes = wav_header + pcm_data

            result = transcribe_audio(wav_bytes, language=self.config.language, audio_format="wav")
            return TranscriptEvent(
                text=result.get("text", ""),
                is_final=True,
                language=result.get("language"),
                confidence=result.get("confidence", 0.0),
            )
        except Exception as e:
            logger.error(f"[AudioPipeline] Transcription error: {e}")
            return None

    def reset(self):
        """Reset pipeline state for a new session."""
        self._speech_buffer = []
        if self._vad_processor:
            self._vad_processor.reset()
        logger.debug("[AudioPipeline] Reset")

    @property
    def is_healthy(self) -> bool:
        return self._is_initialized


def get_pipeline_health() -> dict:
    """Return pipeline component health status for /health endpoint."""
    from vad_service import get_vad_model
    from asr_service import get_whisper_model

    vad_model = get_vad_model()
    whisper_model, whisper_error = get_whisper_model()

    return {
        "vad": {
            "status": "ok" if vad_model is not None else "unavailable",
        },
        "asr": {
            "status": "ok" if whisper_model is not None else "unavailable",
            "error": whisper_error,
        },
        "pipeline": {
            "status": "ok" if (vad_model is not None and whisper_model is not None) else "degraded",
        }
    }
