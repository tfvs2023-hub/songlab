"""VocalSet indexing helpers shared by the extraction and evaluation scripts."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from math import gcd
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

# The ten techniques every VocalSet singer performs (same label set as MARBLE).
TECHNIQUES = (
    "belt",
    "breathy",
    "inhaled",
    "lip_trill",
    "spoken",
    "straight",
    "trill",
    "trillo",
    "vibrato",
    "vocal_fry",
)

_SINGER_RE = re.compile(r"^[fm]\d+$")


@dataclass(frozen=True)
class Clip:
    path: Path
    singer: str
    technique: str


def _normalise(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def index_vocalset(root: Path) -> List[Clip]:
    """Collect (path, singer, technique) for every usable VocalSet wav under ``root``.

    ``root`` should be the ``FULL`` directory of VocalSet (``FULL/<singer>/<context>/<technique>/*.wav``).
    The singer is taken from the first path component that looks like ``f1``/``m11`` (falling back to
    the file-name prefix) and the technique from the wav's parent directory; clips outside
    :data:`TECHNIQUES` are skipped. Files that appear more than once (the release zips also ship
    by-technique / by-vowel copies) are kept only once, keyed by file name.
    """
    root = Path(root)
    clips: List[Clip] = []
    seen = set()
    for path in sorted(root.rglob("*.wav")):
        if path.name.startswith("._") or path.name.lower() in seen:
            continue
        parts = path.relative_to(root).parts[:-1] + (path.name.split("_")[0],)
        singer = next((p.lower() for p in parts if _SINGER_RE.match(p.lower())), None)
        technique = _normalise(path.parent.name)
        if singer is None or technique not in TECHNIQUES:
            continue
        seen.add(path.name.lower())
        clips.append(Clip(path=path, singer=singer, technique=technique))
    if not clips:
        raise FileNotFoundError(f"No VocalSet clips found under {root}. Point --data-root at VocalSet/FULL.")
    return clips


def describe(clips: List[Clip]) -> str:
    singers = sorted({c.singer for c in clips})
    counts = Counter(c.technique for c in clips)
    lines = [f"{len(clips)} clips, {len(singers)} singers"]
    lines += [f"  {t:<10} {counts.get(t, 0)}" for t in TECHNIQUES]
    return "\n".join(lines)


def load_audio(path: Path, target_sr: int) -> np.ndarray:
    """Read a wav as mono float32 at ``target_sr``."""
    signal, sr = sf.read(path, always_2d=False, dtype="float32")
    if signal.ndim > 1:
        signal = signal.mean(axis=1)
    if sr != target_sr:
        g = gcd(sr, target_sr)
        signal = resample_poly(signal, target_sr // g, sr // g)
    return np.asarray(signal, dtype=np.float32)
