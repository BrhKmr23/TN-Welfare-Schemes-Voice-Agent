import time
import tempfile
from typing import Callable, List, Optional

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

from app.config import (
    CHUNK_DURATION,
    MAX_RECORD_TIME,
    MIN_RECORD_TIME,
    SAMPLE_RATE,
    SILENCE_DURATION,
    SILENCE_THRESHOLD,
)


StatusFn = Callable[[str], None]


def list_audio_devices() -> List[dict]:
    """Return available audio devices."""
    return sd.query_devices()


def set_input_device(device_index: int) -> None:
    """Set the default input device index for recording."""
    current = sd.default.device
    if isinstance(current, tuple):
        sd.default.device = (device_index, current[1])
    else:
        sd.default.device = device_index



def record_until_silence(
    silence_threshold: float = SILENCE_THRESHOLD,
    min_record_time: float = MIN_RECORD_TIME,
    max_record_time: float = MAX_RECORD_TIME,
    status_cb: Optional[StatusFn] = None,
) -> Optional[str]:
    """Stream from mic until silence or timeout and return wav path."""
    audio_frames = []
    silent_time = 0.0

    def _say(msg: str) -> None:
        if status_cb:
            status_cb(msg)

    def callback(indata, frames, time_info, status):
        nonlocal silent_time

        energy = float(np.mean(np.abs(indata)))
        audio_frames.append(indata.copy())

        if energy < silence_threshold:
            silent_time += frames / SAMPLE_RATE
        else:
            silent_time = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=callback,
        blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
    ):
        start_time = time.time()
        while True:
            time.sleep(0.1)
            elapsed = time.time() - start_time

            if elapsed > max_record_time:
                _say("Max recording time reached")
                break

            if elapsed > min_record_time and silent_time > SILENCE_DURATION:
                _say("Silence detected, stopping")
                break

    if not audio_frames:
        return None

    audio = np.concatenate(audio_frames, axis=0).flatten()
    max_val = float(np.max(np.abs(audio))) if audio.size else 0.0
    audio_out = np.int16(audio / max_val * 32767) if max_val > 0 else np.int16(audio)

    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    write(temp_wav.name, SAMPLE_RATE, audio_out)
    return temp_wav.name

