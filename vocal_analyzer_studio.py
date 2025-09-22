"""
Studio Vocal Analysis Engine
스튜디오/고품질 녹음용 정밀 분석
폰 녹음과 다른 기준 적용
"""

import warnings
from typing import Dict, Optional, Tuple

import numpy as np
import parselmouth
import pyloudnorm as pyln
import scipy.signal as signal
import scipy.stats as stats
import soundfile as sf
from parselmouth.praat import call

warnings.filterwarnings("ignore")


class VocalAnalyzerStudio:
    """
    Studio 엔진: 고품질 녹음용 정밀 분석
    더 넓은 주파수 대역, HNR 포함, 세밀한 분석
    """

    def __init__(self, sample_rate: int = 44100):
        self.sr = sample_rate  # 스튜디오는 44.1kHz 유지
        self.target_lufs = -16.0  # 스튜디오 기준 (더 높음)
        self.meter = pyln.Meter(self.sr)

    def preprocess(self, audio: np.ndarray, sr_orig: int) -> Tuple[np.ndarray, Dict]:
        """
        스튜디오 전처리 파이프라인
        더 넓은 대역 보존, 최소한의 처리
        """
        # Mono 변환
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # 리샘플링 (44.1kHz 유지 또는 48kHz)
        if sr_orig != self.sr:
            import resampy

            audio = resampy.resample(audio, sr_orig, self.sr)

        # Loudness normalization to -16 LUFS (스튜디오 기준)
        try:
            loudness = self.meter.integrated_loudness(audio)
            if not np.isnan(loudness) and not np.isinf(loudness):
                audio = pyln.normalize.loudness(audio, loudness, self.target_lufs)
        except:
            pass

        # Wider bandpass filter 20-20000 Hz (스튜디오 전체 대역)
        nyquist = self.sr / 2
        low_freq = 20
        high_freq = min(20000, nyquist * 0.95)
        sos = signal.butter(
            4, [low_freq, high_freq], btype="band", fs=self.sr, output="sos"
        )
        audio = signal.sosfilt(sos, audio)

        # Gentle pre-emphasis 0.95 (폰보다 약함)
        audio = np.append(audio[0], audio[1:] - 0.95 * audio[:-1])

        # 품질 메타데이터 계산 (더 엄격한 기준)
        quality = self._compute_quality_meta(audio)

        return audio, quality

    def _compute_quality_meta(self, audio: np.ndarray) -> Dict:
        """스튜디오 품질 메타데이터"""
        # LUFS
        try:
            lufs = self.meter.integrated_loudness(audio)
        except:
            lufs = -30.0

        # SNR 추정 (더 정밀한 방법)
        # 스펙트럼 기반 노이즈 플로어 추정
        f, psd = signal.welch(audio, self.sr, nperseg=4096)
        noise_band = psd[f > 15000]  # 15kHz 이상은 주로 노이즈
        if len(noise_band) > 0:
            noise_floor = np.median(noise_band)
            signal_band = psd[(f > 100) & (f < 8000)]  # 주요 신호 대역
            signal_power = np.mean(signal_band)
            snr = 10 * np.log10(signal_power / (noise_floor + 1e-10))
        else:
            snr = 40.0  # 기본값

        # 클리핑 비율 (더 엄격)
        clipping_ratio = np.sum(np.abs(audio) > 0.99) / len(audio) * 100

        # 무음 비율 (더 엄격)
        silence_ratio = np.sum(np.abs(audio) < 0.001) / len(audio) * 100

        # Dynamic range
        dr = np.percentile(np.abs(audio), 95) / np.percentile(np.abs(audio), 20)

        return {
            "lufs": float(lufs),
            "snr": float(snr),
            "clipping_percent": float(clipping_ratio),
            "silence_percent": float(silence_ratio),
            "dynamic_range": float(20 * np.log10(dr + 1e-10)),
        }

    def extract_features(self, audio: np.ndarray) -> Dict:
        """
        스튜디오 피처 추출
        HNR 포함, 더 정밀한 분석
        """
        features = {}

        # STFT 파워스펙트럼 (더 높은 해상도)
        nperseg = min(4096, len(audio) // 4)
        f, t, Sxx = signal.spectrogram(audio, self.sr, nperseg=nperseg)
        power_spec = np.mean(Sxx, axis=1)

        # Extended frequency bands
        freq_bins = {
            "sub": (20, 80),  # 서브베이스
            "low": (80, 250),  # 베이스
            "low_mid": (250, 800),  # 로우미드
            "mid": (800, 2500),  # 미드
            "high_mid": (2500, 6000),  # 하이미드
            "high": (6000, 12000),  # 하이
            "air": (12000, 20000),  # 에어
        }

        for band_name, (f_low, f_high) in freq_bins.items():
            idx = np.where((f >= f_low) & (f <= f_high))[0]
            if len(idx) > 0:
                features[f"{band_name}_power"] = np.mean(power_spec[idx])
            else:
                features[f"{band_name}_power"] = 0.0

        # Spectral features
        total_power = np.sum(power_spec) + 1e-10
        features["spectral_centroid"] = np.sum(f * power_spec) / total_power
        features["spectral_rolloff"] = self._compute_spectral_rolloff(power_spec, f)
        features["spectral_flux"] = self._compute_spectral_flux(Sxx)
        features["spectral_contrast"] = self._compute_spectral_contrast(power_spec)

        # HNR (Harmonics-to-Noise Ratio) - 스튜디오에서는 사용
        features["hnr"] = self._compute_hnr(audio)

        # Jitter and Shimmer (더 정밀)
        features["jitter"], features["shimmer"] = self._compute_jitter_shimmer(audio)

        # CPP (Cepstral Peak Prominence)
        features["cpp"] = self._compute_cpp(audio)

        # Formants (포먼트 분석)
        features["f1"], features["f2"], features["f3"] = self._compute_formants(audio)

        # MFCC features (음색 특성)
        mfccs = self._compute_mfcc(audio)
        for i, mfcc in enumerate(mfccs[:13]):
            features[f"mfcc_{i}"] = mfcc

        # Pitch features
        features["pitch_mean"], features["pitch_std"] = self._compute_pitch_stats(audio)

        # RMS energy statistics
        frame_size = int(0.02 * self.sr)
        rms_frames = []
        for i in range(0, len(audio) - frame_size, frame_size // 2):
            frame = audio[i : i + frame_size]
            rms_frames.append(np.sqrt(np.mean(frame**2)))

        if rms_frames:
            features["rms_mean"] = np.mean(rms_frames)
            features["rms_std"] = np.std(rms_frames)
            features["rms_skew"] = stats.skew(rms_frames)

        return features

    def _compute_spectral_rolloff(self, power_spec, freqs):
        """스펙트럴 롤오프 계산"""
        cumsum = np.cumsum(power_spec)
        threshold = 0.85 * cumsum[-1]
        idx = np.where(cumsum >= threshold)[0]
        if len(idx) > 0:
            return freqs[idx[0]]
        return freqs[-1]

    def _compute_spectral_flux(self, Sxx):
        """스펙트럴 플럭스 계산"""
        flux = np.sum(np.diff(Sxx, axis=1) ** 2, axis=0)
        return np.mean(flux)

    def _compute_spectral_contrast(self, power_spec):
        """스펙트럴 컨트라스트 계산"""
        n_bands = 6
        band_size = len(power_spec) // n_bands
        contrasts = []

        for i in range(n_bands):
            band = power_spec[i * band_size : (i + 1) * band_size]
            if len(band) > 0:
                peak = np.percentile(band, 95)
                valley = np.percentile(band, 5)
                contrast = peak / (valley + 1e-10)
                contrasts.append(20 * np.log10(contrast + 1e-10))

        return np.mean(contrasts) if contrasts else 0.0

    def _compute_hnr(self, audio):
        """HNR 계산 (스튜디오 환경)"""
        try:
            sound = parselmouth.Sound(audio, self.sr)
            harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
            hnr = call(harmonicity, "Get mean", 0, 0)
            return float(hnr) if not np.isnan(hnr) else 0.0
        except:
            return 0.0

    def _compute_jitter_shimmer(self, audio):
        """Jitter와 Shimmer 계산"""
        try:
            sound = parselmouth.Sound(audio, self.sr)
            pitch = call(sound, "To Pitch", 0.0, 75, 600)
            pulses = call([sound, pitch], "To PointProcess (cc)")

            jitter = call(pulses, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
            shimmer = call(
                [sound, pulses], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
            )

            return float(jitter * 100), float(shimmer * 100)
        except:
            return 0.0, 0.0

    def _compute_cpp(self, audio):
        """CPP 계산 (더 정밀한 버전)"""
        try:
            windowed = audio * signal.windows.hann(len(audio))
            spectrum = np.fft.rfft(windowed, n=8192)  # 더 높은 해상도
            log_spectrum = np.log(np.abs(spectrum) + 1e-10)
            cepstrum = np.fft.irfft(log_spectrum)

            # 50-500 Hz 범위
            min_q = int(self.sr / 500)
            max_q = int(self.sr / 50)

            if max_q < len(cepstrum):
                cepstrum_range = cepstrum[min_q:max_q]
                if len(cepstrum_range) > 0:
                    peak = np.max(cepstrum_range)
                    baseline = np.median(cepstrum_range)
                    cpp = 20 * np.log10(peak / (baseline + 1e-10))
                    if not np.isnan(cpp) and not np.isinf(cpp):
                        return float(cpp)
        except:
            pass
        return 0.0

    def _compute_formants(self, audio):
        """포먼트 주파수 계산"""
        try:
            sound = parselmouth.Sound(audio, self.sr)
            formants = call(sound, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)

            f1 = call(formants, "Get mean", 1, 0, 0, "hertz")
            f2 = call(formants, "Get mean", 2, 0, 0, "hertz")
            f3 = call(formants, "Get mean", 3, 0, 0, "hertz")

            return (
                float(f1) if not np.isnan(f1) else 0.0,
                float(f2) if not np.isnan(f2) else 0.0,
                float(f3) if not np.isnan(f3) else 0.0,
            )
        except:
            return 0.0, 0.0, 0.0

    def _compute_mfcc(self, audio):
        """MFCC 계산"""
        try:
            # Simple MFCC implementation
            from scipy.fftpack import dct

            # Mel filterbank
            n_mels = 26
            n_fft = 2048

            # Compute power spectrum
            frames = []
            hop_length = n_fft // 2
            for i in range(0, len(audio) - n_fft, hop_length):
                frame = audio[i : i + n_fft] * signal.windows.hann(n_fft)
                frames.append(np.abs(np.fft.rfft(frame)) ** 2)

            if frames:
                power_spec = np.mean(frames, axis=0)

                # Mel scale
                mel_spec = np.dot(
                    self._mel_filterbank(n_mels, n_fft, self.sr), power_spec
                )
                log_mel = np.log(mel_spec + 1e-10)

                # DCT to get MFCCs
                mfccs = dct(log_mel, type=2, norm="ortho")
                return mfccs
        except:
            pass

        return np.zeros(13)

    def _mel_filterbank(self, n_filters, n_fft, sr):
        """멜 필터뱅크 생성"""
        mel_points = np.linspace(0, 2595 * np.log10(1 + sr / 2 / 700), n_filters + 2)
        hz_points = 700 * (10 ** (mel_points / 2595) - 1)

        bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)
        filters = np.zeros((n_filters, n_fft // 2 + 1))

        for i in range(1, n_filters + 1):
            left = bin_points[i - 1]
            center = bin_points[i]
            right = bin_points[i + 1]

            for j in range(left, center):
                filters[i - 1, j] = (j - left) / (center - left)
            for j in range(center, right):
                filters[i - 1, j] = (right - j) / (right - center)

        return filters

    def _compute_pitch_stats(self, audio):
        """피치 통계 계산"""
        try:
            sound = parselmouth.Sound(audio, self.sr)
            pitch = call(sound, "To Pitch", 0.0, 75, 600)
            pitch_values = pitch.selected_array["frequency"]
            voiced = pitch_values[pitch_values > 0]

            if len(voiced) > 0:
                return float(np.mean(voiced)), float(np.std(voiced))
        except:
            pass
        return 0.0, 0.0

    def compute_scores(self, features: Dict) -> Dict:
        """
        4축 점수 계산 (스튜디오 기준)
        """
        # 밝기: 고주파 에너지 + spectral centroid + formant
        brightness = 0.0
        brightness += 40 * np.tanh(
            (features.get("high_power", 0) + features.get("air_power", 0)) * 10
        )
        brightness += 30 * np.tanh(
            (features.get("spectral_centroid", 1000) - 2000) / 1000
        )
        brightness += 30 * np.tanh((features.get("f2", 1500) - 2200) / 500)

        # 두께: 저주파 에너지 + 낮은 포먼트 + spectral contrast
        thickness = 0.0
        thickness += 40 * np.tanh(
            (features.get("low_power", 0) + features.get("low_mid_power", 0)) * 10
        )
        thickness += 30 * np.tanh((1000 - features.get("f1", 700)) / 300)
        thickness += 30 * np.tanh(features.get("spectral_contrast", 0) / 10)

        # 음압: RMS + dynamic range
        loudness = 0.0
        loudness += 60 * np.tanh(features.get("rms_mean", 0) * 20)
        loudness += 40 * np.tanh(features.get("dynamic_range", 0) / 20)

        # 선명도: HNR + CPP + low jitter/shimmer
        clarity = 0.0
        clarity += 40 * np.tanh(features.get("hnr", 0) / 10)
        clarity += 30 * np.tanh(features.get("cpp", 0) / 10)
        clarity += 15 * np.tanh((1 - features.get("jitter", 0) / 2))
        clarity += 15 * np.tanh((1 - features.get("shimmer", 0) / 5))

        return {
            "brightness": float(np.clip(brightness, -100, 100)),
            "thickness": float(np.clip(thickness, -100, 100)),
            "loudness": float(np.clip(loudness, -100, 100)),
            "clarity": float(np.clip(clarity, -100, 100)),
        }

    def compute_confidence(self, quality: Dict) -> float:
        """
        스튜디오 신뢰도 계산
        """
        confidence = 1.0

        # SNR (스튜디오는 40dB 이상 기대)
        if quality["snr"] < 40:
            confidence *= quality["snr"] / 40

        # 클리핑 (매우 엄격)
        if quality["clipping_percent"] > 0.1:
            confidence *= 0.5

        # Dynamic range
        if quality.get("dynamic_range", 20) < 20:
            confidence *= 0.8

        return float(np.clip(confidence, 0, 1))

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

            # 피처 추출
            features = self.extract_features(audio_processed)

            # 점수 계산
            scores = self.compute_scores(features)

            # 신뢰도 계산
            confidence = self.compute_confidence(quality)

            return {
                "scores": scores,
                "confidence": confidence,
                "quality": quality,
                "engine": "studio",
                "features_summary": {
                    "hnr": features.get("hnr", 0),
                    "jitter": features.get("jitter", 0),
                    "shimmer": features.get("shimmer", 0),
                    "f1": features.get("f1", 0),
                    "f2": features.get("f2", 0),
                    "f3": features.get("f3", 0),
                    "pitch_mean": features.get("pitch_mean", 0),
                },
            }

        except Exception as e:
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
                    "dynamic_range": 0.0,
                },
                "engine": "studio",
                "error": str(e),
            }
