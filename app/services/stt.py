import functools
import whisper

from app.config import LANG_TAMIL


@functools.lru_cache(maxsize=1)
def load_model(model_size: str = "small"):
    """Lazy-load Whisper model once per process."""
    return whisper.load_model(model_size)


def speech_to_text(audio_path: str, model_size: str = "small") -> tuple[str, float]:
    """
    Convert Tamil speech to text.
    
    Returns:
        (text, confidence): Tuple of recognized text and confidence score (0.0-1.0)
    """
    model = load_model(model_size)
    result = model.transcribe(audio_path, language=LANG_TAMIL, fp16=False)
    text = result["text"].strip()
    
    # Calculate confidence from Whisper's average log probability
    # Whisper returns segments with avg_logprob, convert to confidence (0-1)
    segments = result.get("segments", [])
    if segments:
        # Average log probability across all segments
        avg_logprob = sum(seg.get("avg_logprob", -1.0) for seg in segments) / len(segments)
        # Convert log probability to confidence (rough heuristic)
        # logprob typically ranges from -1.0 (low) to 0.0 (high)
        # Map to 0.0-1.0: confidence = (logprob + 1.0) / 1.0, clamped
        confidence = max(0.0, min(1.0, (avg_logprob + 1.0)))
    else:
        # Fallback: if no segments, use text length as heuristic
        confidence = 0.7 if len(text) > 5 else 0.3
    
    return text, confidence

