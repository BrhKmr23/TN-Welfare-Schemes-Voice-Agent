import tempfile
from gtts import gTTS

from app.config import LANG_TAMIL


def text_to_speech(text: str) -> str:
    """Return path to a temp mp3 synthesized in Tamil."""
    tts = gTTS(text=text, lang=LANG_TAMIL)
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_mp3.name)
    return temp_mp3.name

