"""Debug helper: run VocalAnalyzerLite.preprocess on a WAV file and print quality info."""

import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import soundfile as sf

from vocal_analyzer_lite import VocalAnalyzerLite


def run(path):
    va = VocalAnalyzerLite()
    with open(path, "rb") as f:
        data = f.read()

    # load with soundfile exactly like analyzer
    audio, sr = sf.read(io.BytesIO(data))
    print(f"loaded: sr={sr}, len={len(audio)}")

    audio_proc, quality = va.preprocess(audio, sr)

    print(f"processed len: {len(audio_proc)}")
    print("quality:")
    for k, v in quality.items():
        print(f"  {k}: {v}")

    # write processed audio for inspection
    out = Path(path).with_suffix(".proc.wav")
    try:
        sf.write(str(out), audio_proc, 16000)
        print(f"wrote processed file: {out}")
    except Exception as e:
        print("failed writing processed file:", e)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: debug_preprocess.py /path/to/file.wav")
        sys.exit(2)
    run(sys.argv[1])
