"""
PRISM ASR Service — Faster Whisper speech-to-text.
Accurate Hindi/English/Hinglish transcription, runs on CPU.
Model downloads ~1.5GB on first use (cached after).
"""
import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_loaded = False
_whisper_error = None


def get_whisper_model():
    """Load and cache Faster Whisper model. Returns (model, error)."""
    global _whisper_model, _whisper_loaded, _whisper_error
    if _whisper_loaded:
        return _whisper_model, _whisper_error

    model_size = os.getenv("WHISPER_MODEL_SIZE", "medium")
    try:
        from faster_whisper import WhisperModel
        logger.info(f"[PRISM ASR] Loading '{model_size}' (CPU int8)...")
        _whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            download_root=os.path.join(os.path.dirname(__file__), ".whisper_cache"),
        )
        _whisper_loaded = True
        logger.info("[PRISM ASR] Model ready")
        return _whisper_model, None
    except ImportError:
        _whisper_error = "faster-whisper not installed"
        _whisper_loaded = True
        logger.warning(f"[PRISM ASR] {_whisper_error}")
        return None, _whisper_error
    except Exception as e:
        _whisper_error = str(e)
        _whisper_loaded = True
        logger.error(f"[PRISM ASR] {e}")
        return None, _whisper_error


def transcribe_audio(audio_bytes: bytes, language: Optional[str] = None, audio_format: str = "webm") -> dict:
    """
    Transcribe audio bytes. Auto-detects Hindi/English/Hinglish.
    Returns: {text, language, confidence, segments, error}
    """
    model, error = get_whisper_model()
    if model is None:
        return {"text": "", "language": language or "unknown", "confidence": 0.0, "segments": [], "error": error}

    suffix = f".{audio_format}" if not audio_format.startswith(".") else audio_format
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "vad_parameters": {"min_silence_duration_ms": 300},
        }
        lang_map = {"hi": "hi", "en": "en", "hi-IN": "hi", "en-IN": "en", "en-US": "en"}
        if language:
            mapped = lang_map.get(language, language[:2])
            if mapped:
                kwargs["language"] = mapped

        segments, info = model.transcribe(tmp_path, **kwargs)
        seg_list = []
        parts = []
        for seg in segments:
            seg_list.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
            parts.append(seg.text.strip())

        return {
            "text": " ".join(parts).strip(),
            "language": info.language,
            "confidence": float(info.language_probability),
            "segments": seg_list,
            "error": None,
        }
    except Exception as e:
        logger.error(f"[PRISM ASR] Transcription error: {e}")
        return {"text": "", "language": language or "unknown", "confidence": 0.0, "segments": [], "error": str(e)}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
