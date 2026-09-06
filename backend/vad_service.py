"""
PRISM VAD Service — Silero Voice Activity Detection.
Detects speech start/end from raw 16kHz PCM audio.
Used for barge-in detection (user interrupts PRISM mid-response).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_vad_model = None
_vad_loaded = False


def get_vad_model():
    """Load and cache Silero VAD model. Returns None if unavailable."""
    global _vad_model, _vad_loaded
    if _vad_loaded:
        return _vad_model
    try:
        from silero_vad import load_silero_vad
        _vad_model = load_silero_vad()
        _vad_loaded = True
        logger.info("[PRISM VAD] Model loaded")
        return _vad_model
    except ImportError:
        logger.warning("[PRISM VAD] silero-vad not installed")
        _vad_loaded = True
        return None
    except Exception as e:
        logger.error(f"[PRISM VAD] Load failed: {e}")
        _vad_loaded = True
        return None


class VADProcessor:
    """
    Stateful per-connection VAD processor.
    Accepts 16kHz 16-bit PCM chunks, fires speech_start / speech_end events.
    """
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 512
    SPEECH_THRESHOLD = 0.5

    def __init__(self, model, silence_duration_ms: int = 480, min_speech_duration_ms: int = 150, max_utterance_duration_ms: int = 15000):
        self.model = model
        self.is_speaking = False
        self.silence_count = 0
        # Configuration
        self.silence_duration_ms = silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.max_utterance_duration_ms = max_utterance_duration_ms
        # Derived counts (at 16kHz, 512 samples = 32ms per chunk)
        self._chunk_duration_ms = (self.CHUNK_SIZE / self.SAMPLE_RATE) * 1000
        self._silence_chunks_needed = max(1, int(silence_duration_ms / self._chunk_duration_ms))
        self._max_utterance_chunks = max(1, int(max_utterance_duration_ms / self._chunk_duration_ms))
        # State
        self.utterance_chunk_count = 0
        self.noise_floor: float = 0.0
        self.is_barge_in_mode: bool = False
        import numpy as np
        self.buffer = np.array([], dtype=np.float32)

    def process_chunk(self, raw_bytes: bytes) -> list:
        import numpy as np
        import torch
        events = []
        # When is_barge_in_mode=True and speech is detected, emits {"event": "barge_in"}
        # in addition to speech_start. Frontend uses this to transition from SPEAKING -> LISTENING.
        # Agora Conversational AI handles the actual audio-level interruption natively.
        try:
            audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            self.buffer = np.concatenate([self.buffer, audio_float])

            while len(self.buffer) >= self.CHUNK_SIZE:
                chunk = self.buffer[:self.CHUNK_SIZE]
                self.buffer = self.buffer[self.CHUNK_SIZE:]
                tensor = torch.from_numpy(chunk).unsqueeze(0)
                with torch.no_grad():
                    prob = self.model(tensor, self.SAMPLE_RATE).item()

                if prob >= self.SPEECH_THRESHOLD:
                    self.silence_count = 0
                    if not self.is_speaking:
                        self.is_speaking = True
                        self.utterance_chunk_count = 0
                        events.append({"event": "speech_start"})
                        if self.is_barge_in_mode:
                            events.append({"event": "barge_in"})
                    else:
                        # Track utterance duration while speaking
                        self.utterance_chunk_count += 1
                        # Enforce max utterance duration
                        if self.utterance_chunk_count >= self._max_utterance_chunks:
                            self.is_speaking = False
                            self.silence_count = 0
                            self.utterance_chunk_count = 0
                            events.append({"event": "turn_complete", "reason": "max_utterance_exceeded"})
                else:
                    if self.is_speaking:
                        self.utterance_chunk_count += 1
                        self.silence_count += 1
                        if self.silence_count >= self._silence_chunks_needed:
                            self.is_speaking = False
                            self.silence_count = 0
                            self.utterance_chunk_count = 0
                            events.append({"event": "speech_end"})
        except Exception as e:
            events.append({"event": "error", "message": str(e)})
        return events

    def reset(self):
        import numpy as np
        self.is_speaking = False
        self.silence_count = 0
        self.utterance_chunk_count = 0
        self.buffer = np.array([], dtype=np.float32)
