"""Vocal analysis utilities built on pyworld and CREPE."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import crepe
import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import find_peaks, resample_poly


@dataclass
class VocalMetrics:
    """Container for the extracted vocal metrics."""

    f1_hz: float
    f2_hz: float
    f3_hz: float
    chest_head_ratio: float
    clarity: float
    power_db: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class PyWorldVocalAnalyzer:
    """Analyze vocal recordings using pyworld for timbre features and CREPE for F0."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_period_ms: float = 5.0,
        confidence_threshold: float = 0.5,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_period_ms = frame_period_ms
        self.confidence_threshold = confidence_threshold

    def _load_audio(self, path: Path) -> Tuple[np.ndarray, int]:
        signal, sr = sf.read(path, always_2d=False)
        if signal.ndim > 1:
            signal = np.mean(signal, axis=1)
        signal = signal.astype(np.float64)
        # Normalise if needed
        peak = np.max(np.abs(signal))
        if peak > 1.0:
            signal = signal / peak
        if sr != self.sample_rate:
            signal = resample_poly(signal, self.sample_rate, sr).astype(np.float64)
            sr = self.sample_rate
        return signal, sr

    def _extract_f0_with_crepe(self, signal: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        step_size = self.frame_period_ms
        time, frequency, confidence, _ = crepe.predict(
            signal,
            sr,
            step_size=step_size,
            model_capacity="full",
            viterbi=True,
        )
        voiced_frequency = frequency.copy()
        voiced_frequency[confidence < self.confidence_threshold] = 0.0
        return voiced_frequency.astype(np.float64), time.astype(np.float64), confidence.astype(np.float64)

    def analyze(self, audio_path: Path) -> VocalMetrics:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        signal, sr = self._load_audio(audio_path)
        if signal.size == 0:
            raise ValueError("Loaded audio file is empty.")

        f0, time_axis, confidence = self._extract_f0_with_crepe(signal, sr)
        if not np.any(f0 > 0):
            raise ValueError("CREPE did not detect voiced frames; ensure the input contains vocals.")

        spectral_envelope = pw.cheaptrick(signal, f0, time_axis, sr)
        aperiodicity = pw.d4c(signal, f0, time_axis, sr)

        voiced_mask = f0 > 0
        f1, f2, f3 = self._estimate_formants(spectral_envelope, voiced_mask, sr)
        chest_head = self._chest_head_ratio(spectral_envelope, voiced_mask, sr)
        clarity = self._clarity(aperiodicity, voiced_mask)
        power_db = self._power(signal)

        return VocalMetrics(
            f1_hz=f1,
            f2_hz=f2,
            f3_hz=f3,
            chest_head_ratio=chest_head,
            clarity=clarity,
            power_db=power_db,
        )

    @staticmethod
    def _power(signal: np.ndarray) -> float:
        rms = np.sqrt(np.mean(np.square(signal)) + 1e-12)
        return 20.0 * np.log10(rms + 1e-12)

    def _estimate_formants(
        self,
        spectral_envelope: np.ndarray,
        voiced_mask: np.ndarray,
        sr: int,
    ) -> Tuple[float, float, float]:
        freq_axis = np.linspace(0, sr / 2, spectral_envelope.shape[1])
        valid = (freq_axis >= 90.0) & (freq_axis <= 5000.0)

        f1_list: List[float] = []
        f2_list: List[float] = []
        f3_list: List[float] = []

        for frame, is_voiced in zip(spectral_envelope, voiced_mask):
            if not is_voiced:
                continue
            log_spec = 10.0 * np.log10(frame + 1e-12)
            log_spec = log_spec[valid]
            peaks, _ = find_peaks(log_spec, distance=8)
            if peaks.size < 3:
                continue
            freq_candidates = freq_axis[valid][peaks]
            if freq_candidates.size >= 3:
                f1_list.append(freq_candidates[0])
                f2_list.append(freq_candidates[1])
                f3_list.append(freq_candidates[2])

        def average(values: List[float], fallback: float) -> float:
            return float(np.mean(values)) if values else fallback

        return (
            average(f1_list, float("nan")),
            average(f2_list, float("nan")),
            average(f3_list, float("nan")),
        )

    def _chest_head_ratio(
        self,
        spectral_envelope: np.ndarray,
        voiced_mask: np.ndarray,
        sr: int,
    ) -> float:
        freq_axis = np.linspace(0, sr / 2, spectral_envelope.shape[1])
        low_band = (freq_axis >= 80.0) & (freq_axis <= 500.0)
        high_band = (freq_axis > 500.0) & (freq_axis <= 3000.0)

        ratios = []
        for frame, is_voiced in zip(spectral_envelope, voiced_mask):
            if not is_voiced:
                continue
            low_energy = np.sum(frame[low_band])
            high_energy = np.sum(frame[high_band])
            if high_energy <= 0:
                continue
            ratios.append(low_energy / (high_energy + 1e-12))

        if not ratios:
            return float("nan")
        return float(np.mean(ratios))

    @staticmethod
    def _clarity(aperiodicity: np.ndarray, voiced_mask: np.ndarray) -> float:
        voiced_ap = aperiodicity[voiced_mask]
        if voiced_ap.size == 0:
            return float("nan")
        harmonic_ratio = 1.0 - np.clip(voiced_ap, 0.0, 1.0)
        return float(np.mean(harmonic_ratio))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze vocal metrics using pyworld and CREPE.")
    parser.add_argument("audio", type=Path, help="Path to the input WAV/FLAC file")
    parser.add_argument(
        "--frame-period",
        type=float,
        default=5.0,
        help="Frame period for analysis in milliseconds (default: 5.0)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Target sample rate for analysis (default: 16000)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Confidence threshold for CREPE voiced detection (default: 0.5)",
    )

    args = parser.parse_args()
    analyzer = PyWorldVocalAnalyzer(
        sample_rate=args.sample_rate,
        frame_period_ms=args.frame_period,
        confidence_threshold=args.confidence_threshold,
    )
    metrics = analyzer.analyze(args.audio)
    for key, value in metrics.to_dict().items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
