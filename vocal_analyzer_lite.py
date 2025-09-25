"""
Lite Vocal Analysis Engine
규칙+통계 기반, 폰 녹음에 최적화
빠르고 강건한 4축 분석: 밝기, 두께, 음압, 선명도
"""

import numpy as np
import parselmouth
import scipy.signal as signal
import scipy.stats as stats
import soundfile as sf
from parselmouth.praat import call

# import webrtcvad  # Optional, will use simple energy-based VAD if not available
try:
    import webrtcvad

    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
import warnings
from typing import Dict, Optional, Tuple

import pyloudnorm as pyln

warnings.filterwarnings("ignore")


class VocalAnalyzerLite:
    """
    Lite 엔진: 규칙+통계 기반 4축 분석
    CPU 친화적, 폰 잡음에 강건
    """

    def __init__(self, sample_rate: int = 16000):
        self.sr = sample_rate
        from config import TARGET_LUFS

        self.target_lufs = TARGET_LUFS
        if WEBRTCVAD_AVAILABLE:
            self.vad = webrtcvad.Vad(2)  # 중간 민감도
        else:
            self.vad = None
        self.meter = pyln.Meter(self.sr)

    def preprocess(self, audio: np.ndarray, sr_orig: int) -> Tuple[np.ndarray, Dict]:
        """
        표준 전처리 파이프라인
        mono 16k, loudnorm -23 LUFS, 80-8000 Hz, pre-emphasis 0.97
        """
        # Mono 변환
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # 리샘플링 to 16kHz
        if sr_orig != self.sr:
            import resampy

            audio = resampy.resample(audio, sr_orig, self.sr)

        # Loudness normalization to -23 LUFS
        try:
            loudness = self.meter.integrated_loudness(audio)
            if not np.isnan(loudness) and not np.isinf(loudness):
                audio = pyln.normalize.loudness(audio, loudness, self.target_lufs)
        except:
            pass

        # Bandpass filter 80-8000 Hz (adjust for Nyquist frequency)
        nyquist = self.sr / 2
        low_freq = min(80, nyquist * 0.9)
        high_freq = min(8000, nyquist * 0.9)
        if low_freq < high_freq:
            sos = signal.butter(
                4, [low_freq, high_freq], btype="band", fs=self.sr, output="sos"
            )
            audio = signal.sosfilt(sos, audio)

        # Pre-emphasis 0.97
        audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])

        # VAD trimming
        audio_trimmed = self._vad_trim(audio)
        if len(audio_trimmed) > int(0.1 * self.sr):  # 최소 0.1초
            audio = audio_trimmed

        # 품질 메타데이터 계산
        quality = self._compute_quality_meta(audio)

        return audio, quality

    def _vad_trim(self, audio: np.ndarray) -> np.ndarray:
        """VAD 기반 트리밍"""
        if self.vad is not None:
            # WebRTC VAD 사용
            frame_len = int(0.03 * self.sr)  # 30ms frames
            frames = []

            for i in range(0, len(audio) - frame_len, frame_len):
                frame = audio[i : i + frame_len]
                frame_bytes = (frame * 32767).astype(np.int16).tobytes()
                if self.vad.is_speech(frame_bytes, self.sr):
                    frames.append(frame)

            if frames:
                return np.concatenate(frames)
        else:
            # Simple energy-based VAD fallback
            frame_len = int(0.03 * self.sr)
            energy_threshold = np.mean(np.abs(audio)) * 0.3
            frames = []

            for i in range(0, len(audio) - frame_len, frame_len):
                frame = audio[i : i + frame_len]
                if np.mean(np.abs(frame)) > energy_threshold:
                    frames.append(frame)

            if frames:
                return np.concatenate(frames)

        return audio

    def _compute_quality_meta(self, audio: np.ndarray) -> Dict:
        """품질 메타데이터 계산"""
        # LUFS
        try:
            lufs = self.meter.integrated_loudness(audio)
        except:
            lufs = -30.0

        # SNR 추정 (간단 버전)
        noise_floor = np.percentile(np.abs(audio), 10)
        signal_peak = np.percentile(np.abs(audio), 90)
        snr = 20 * np.log10(signal_peak / (noise_floor + 1e-10))

        # 클리핑 비율
        clipping_ratio = np.sum(np.abs(audio) > 0.95) / len(audio) * 100

        # 무음 비율
        silence_ratio = np.sum(np.abs(audio) < 0.01) / len(audio) * 100

        return {
            "lufs": float(lufs),
            "snr": float(snr),
            "clipping_percent": float(clipping_ratio),
            "silence_percent": float(silence_ratio),
        }

    def extract_features(self, audio: np.ndarray) -> Dict:
        """
        핵심 피처 추출
        STFT 파워스펙트럼, spectral ratios, CPP, ZCR, pitch metrics
        """
        features = {}

        # STFT 파워스펙트럼
        nperseg = min(512, len(audio) // 4)
        f, t, Sxx = signal.spectrogram(audio, self.sr, nperseg=nperseg)
        power_spec = np.mean(Sxx, axis=1)

        # Frequency band ratios
        freq_bins = {
            "low": (80, 300),
            "mid": (300, 2000),
            "high": (2000, 4000),
            "very_high": (4000, 8000),
        }

        for band_name, (f_low, f_high) in freq_bins.items():
            idx = np.where((f >= f_low) & (f <= f_high))[0]
            if len(idx) > 0:
                features[f"{band_name}_power"] = np.mean(power_spec[idx])
            else:
                features[f"{band_name}_power"] = 0.0

        # Spectral ratios
        total_power = np.sum(power_spec) + 1e-10
        features["low_ratio"] = features["low_power"] / total_power
        features["midhi_ratio"] = (
            features["high_power"] + features["very_high_power"]
        ) / total_power

        # Spectral centroid
        features["spectral_centroid"] = np.sum(f * power_spec) / np.sum(power_spec)

        # RMS energy statistics
        frame_size = int(0.02 * self.sr)  # 20ms frames
        rms_frames = []
        for i in range(0, len(audio) - frame_size, frame_size // 2):
            frame = audio[i : i + frame_size]
            rms_frames.append(np.sqrt(np.mean(frame**2)))

        if rms_frames:
            features["rms_mean"] = np.mean(rms_frames)
            features["rms_std"] = np.std(rms_frames)
        else:
            features["rms_mean"] = 0.0
            features["rms_std"] = 0.0

        # CPP (Cepstral Peak Prominence) - 상대값
        features["cpp_rel"] = self._compute_cpp_relative(audio)

        # ZCR (Zero Crossing Rate)
        zcr = np.mean(np.abs(np.diff(np.sign(audio))) / 2)
        features["zcr"] = zcr

        # Pitch dropout detection
        features["pitch_dropout"] = self._detect_pitch_dropout(audio)

        # Spectral tilt
        features["spectral_tilt"] = self._compute_spectral_tilt(power_spec, f)

        # H1-H2 (simplified Welch method)
        features["h1_h2"] = self._compute_h1_h2_welch(audio)

        return features

    def _compute_cpp_relative(self, audio: np.ndarray) -> float:
        """CPP 상대값 계산 (폰 잡음에 강건)"""
        try:
            # Cepstrum 계산
            windowed = audio * signal.windows.hann(len(audio))
            spectrum = np.fft.rfft(windowed)
            log_spectrum = np.log(np.abs(spectrum) + 1e-10)
            cepstrum = np.fft.irfft(log_spectrum)

            # 50-500 Hz 범위의 quefrency에서 peak 찾기
            min_q = int(self.sr / 500)  # 500 Hz
            max_q = int(self.sr / 50)  # 50 Hz

            if max_q < len(cepstrum):
                cepstrum_range = cepstrum[min_q:max_q]
                if len(cepstrum_range) > 0:
                    peak = np.max(cepstrum_range)
                    baseline = np.median(cepstrum_range)

                    # Ensure argument to log10 is positive to avoid RuntimeWarning
                    argument = peak / (baseline + 1e-10)
                    if argument <= 0:
                        return 0.0

                    cpp = 20 * np.log10(argument)
                    if not np.isnan(cpp) and not np.isinf(cpp):
                        return float(cpp)
        except:
            pass
        return 0.0

    def _detect_pitch_dropout(self, audio: np.ndarray) -> float:
        """피치 드롭아웃 검출"""
        try:
            sound = parselmouth.Sound(audio, self.sr)
            pitch = sound.to_pitch(time_step=0.01)
            pitch_values = pitch.selected_array["frequency"]

            # 유성음 구간에서 피치 없는 비율
            voiced_frames = pitch_values[pitch_values > 0]
            if len(pitch_values) > 0:
                dropout_ratio = 1 - (len(voiced_frames) / len(pitch_values))
                return float(dropout_ratio)
        except:
            pass
        return 0.0

    def _compute_spectral_tilt(
        self, power_spec: np.ndarray, freqs: np.ndarray
    ) -> float:
        """스펙트럴 틸트 계산"""
        try:
            # Log scale
            log_power = np.log(power_spec + 1e-10)
            # Linear regression
            coeffs = np.polyfit(freqs, log_power, 1)
            return float(coeffs[0])  # slope
        except:
            return 0.0

    def _compute_h1_h2_welch(self, audio: np.ndarray) -> float:
        """H1-H2 계산 (Welch method)"""
        try:
            # Welch's method for PSD
            f, psd = signal.welch(audio, self.sr, nperseg=1024)

            # F0 추정
            sound = parselmouth.Sound(audio, self.sr)
            pitch = call(sound, "To Pitch", 0.0, 75, 600)
            f0 = call(pitch, "Get mean", 0, 0, "Hertz")

            if f0 and f0 > 0:
                # H1, H2 주파수 위치
                h1_idx = np.argmin(np.abs(f - f0))
                h2_idx = np.argmin(np.abs(f - 2 * f0))

                if h1_idx < len(psd) and h2_idx < len(psd):
                    h1 = 10 * np.log10(psd[h1_idx] + 1e-10)
                    h2 = 10 * np.log10(psd[h2_idx] + 1e-10)
                    return float(h1 - h2)
        except:
            pass
        return 0.0

    def compute_scores(self, features: Dict) -> Dict:
        """
        4축 점수 계산 (z-score 기반)
        """
        # Reference statistics from config file
        from config import LITE_ENGINE_REF_STATS as ref_stats

        def z_score(value, ref_mean, ref_std):
            return (value - ref_mean) / (ref_std + 1e-10)

        def scale_score(z):
            """tanh scaling to -100 to +100"""
            if np.isnan(z) or np.isinf(z):
                return 0.0
            return 100 * np.tanh(0.75 * z)

        # 밝기 = 0.65·z(midhi) + 0.35·z(centroid)
        z_midhi = z_score(features.get("midhi_ratio", 0), *ref_stats["midhi_ratio"])
        z_centroid = z_score(
            features.get("spectral_centroid", 0), *ref_stats["spectral_centroid"]
        )
        brightness = scale_score(0.65 * z_midhi + 0.35 * z_centroid)

        # 두께 = 0.7·z(low) + 0.3·z(μ_H1H2 - H1H2)
        z_low = z_score(features.get("low_ratio", 0), *ref_stats["low_ratio"])
        z_h1h2 = z_score(
            ref_stats["h1_h2"][0] - features.get("h1_h2", 0), *ref_stats["h1_h2"]
        )
        thickness = scale_score(0.7 * z_low + 0.3 * z_h1h2)

        # 음압 = 0.75·z(RMSmean) + 0.25·z(μ_RMSstd - RMSstd)
        z_rms_mean = z_score(features.get("rms_mean", 0), *ref_stats["rms_mean"])
        z_rms_std = z_score(
            ref_stats["rms_std"][0] - features.get("rms_std", 0), *ref_stats["rms_std"]
        )
        loudness = scale_score(0.75 * z_rms_mean + 0.25 * z_rms_std)

        # 선명도 = 0.70·z(CPP_rel) + 0.15·z(μ_ZCR - ZCR) + 0.15·z(μ_drop - drop)
        z_cpp = z_score(features.get("cpp_rel", 0), *ref_stats["cpp_rel"])
        z_zcr = z_score(ref_stats["zcr"][0] - features.get("zcr", 0), *ref_stats["zcr"])
        z_dropout = z_score(
            ref_stats["pitch_dropout"][0] - features.get("pitch_dropout", 0),
            *ref_stats["pitch_dropout"],
        )
        clarity = scale_score(0.70 * z_cpp + 0.15 * z_zcr + 0.15 * z_dropout)

        return {
            "brightness": float(np.clip(brightness, -100, 100)),
            "thickness": float(np.clip(thickness, -100, 100)),
            "loudness": float(np.clip(loudness, -100, 100)),
            "clarity": float(np.clip(clarity, -100, 100)),
        }

    def compute_confidence(self, quality: Dict, features: Dict) -> float:
        """
        신뢰도 계산
        SNR, 유효구간비, 클리핑, 피처분산 기반
        """
        confidence_factors = []

        # SNR factor (15-40 dB range)
        snr = quality.get("snr", 20)
        snr_conf = np.clip((snr - 15) / 25, 0, 1)
        confidence_factors.append(snr_conf)

        # 유효구간비 (무음이 적을수록 좋음)
        silence = quality.get("silence_percent", 50)
        silence_conf = np.clip(1 - (silence / 100), 0, 1)
        confidence_factors.append(silence_conf)

        # 클리핑 반비례
        clipping = quality.get("clipping_percent", 0)
        clipping_conf = np.clip(1 - (clipping / 5), 0, 1)  # 5% 이상이면 신뢰도 0
        confidence_factors.append(clipping_conf)

        # 피처 분산 반비례 (일관성)
        feature_values = [v for k, v in features.items() if isinstance(v, (int, float))]
        if feature_values:
            feature_cv = np.std(feature_values) / (
                np.mean(np.abs(feature_values)) + 1e-10
            )
            feature_conf = np.clip(1 - feature_cv, 0, 1)
            confidence_factors.append(feature_conf)

        # Sigmoid combination
        if confidence_factors:
            raw_confidence = np.mean(confidence_factors)
            # Sigmoid transform for smoother distribution
            confidence = 1 / (1 + np.exp(-10 * (raw_confidence - 0.5)))
            return float(np.clip(confidence, 0, 1))
        else:
            return 0.5

    def analyze(self, audio_data: bytes) -> Dict:
        """
        메인 분석 함수
        """
        try:
            # 오디오 로드
            import io

            audio, sr = sf.read(io.BytesIO(audio_data))

            # 전처리
            audio_processed, quality = self.preprocess(audio, sr)

            # 품질 게이트
            if (
                quality["snr"] < 15
                or quality["clipping_percent"] > 3
                or quality["silence_percent"] > 60
            ):
                # Low confidence or reject
                confidence = 0.1
            else:
                confidence = None

            # 피처 추출
            features = self.extract_features(audio_processed)

            # 점수 계산
            scores = self.compute_scores(features)

            # 신뢰도 계산
            if confidence is None:
                confidence = self.compute_confidence(quality, features)

            return {
                "scores": scores,
                "confidence": confidence,
                "quality": quality,
                "engine": "lite",
            }

        except Exception as e:
            # 실패 시 기본값
            return {
                "scores": {
                    "brightness": 0.0,
                    "thickness": 0.0,
                    "loudness": 0.0,
                    "clarity": 0.0,
                },
                "confidence": 0.0,
                "quality": {
                    "lufs": -30.0,
                    "snr": 0.0,
                    "clipping_percent": 0.0,
                    "silence_percent": 100.0,
                },
                "engine": "lite",
                "error": str(e),
            }
