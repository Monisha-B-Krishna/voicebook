"""
Live microphone recording, shared by both the initial voice input step
and the spoken confirmation reply step.

Press ENTER to start, speak, press ENTER again to stop.

Every recording is automatically saved into a dedicated category folder
under data/audio/ with a timestamped filename - so nothing overwrites
previous recordings, and this folder naturally becomes your growing
collection of real recorded utterances (useful for the dataset deliverable
later, not just throwaway test files).
"""

import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
from pathlib import Path
from datetime import datetime

SAMPLE_RATE = 16000  # matches Sarvam's expected input

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_ROOT = PROJECT_ROOT / "data" / "audio"


def record_from_mic(category: str, prompt: str = "Press ENTER to START recording...") -> str:
    """
    Records from the mic and saves into data/audio/<category>/ with a
    timestamped filename, e.g. data/audio/live_input/live_input_20260810_225134.wav

    category: one of "live_input", "confirm_reply", or any other label you
    want a dedicated folder for - the folder is created automatically.
    """
    folder = AUDIO_ROOT / category
    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = folder / f"{category}_{timestamp}.wav"

    input(prompt)
    print("Recording... speak now. Press ENTER again to STOP.")

    chunks = []

    def callback(indata, frames, time, status):
        chunks.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback)

    with stream:
        input()

    print("Stopped recording.")

    if not chunks:
        raise RuntimeError("No audio captured.")

    audio = np.concatenate(chunks, axis=0)
    write(str(output_path), SAMPLE_RATE, audio)
    print(f"Saved to {output_path} ({len(audio) / SAMPLE_RATE:.1f}s)")
    return str(output_path)
