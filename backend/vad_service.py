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
    SILENCE_CHUNKS = 8

    def __init__(self, model):
        self.model = model
        self.is_speaking = False
        self.silence_count = 0
        # Lazy import numpy inside class methods
        import numpy as np
        self.buffer = np.array([], dtype=np.float32)

    def process_chunk(self, raw_bytes: bytes) -> list:
        import numpy as np
        import torch
        events = []
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
                        events.append({"event": "speech_start"})
                else:
                    if self.is_speaking:
                        self.silence_count += 1
                        if self.silence_count >= self.SILENCE_CHUNKS:
                            self.is_speaking = False
                            self.silence_count = 0
                            events.append({"event": "speech_end"})
        except Exception as e:
            events.append({"event": "error", "message": str(e)})
        return events

    def reset(self):
        import numpy as np
        self.is_speaking = False
        self.silence_count = 0
        self.buffer = np.array([], dtype=np.float32)
