"""Shared configuration for the Tamil voice agent components."""

SAMPLE_RATE = 16_000
# Based on runtime logs, typical speech energy ~0.004–0.006 and noise ~1e-5,
# so set threshold safely between them so speech is "non-silent".
SILENCE_THRESHOLD = 0.0005
SILENCE_DURATION = 1.2
CHUNK_DURATION = 0.2
MAX_RECORD_TIME = 10.0
MIN_RECORD_TIME = 2.0

# Language codes
LANG_TAMIL = "ta"

