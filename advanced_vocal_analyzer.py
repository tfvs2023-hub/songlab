"""
Advanced 4-Axis Vocal Analysis System
- Brightness (밝기): Spectral centroid + Formant analysis
- Thickness (음색 두께): Harmonic richness + Spectral complexity
- Adduction (성대 내전): HNR + Jitter/Shimmer analysis
- SPL (음압): RMS + LUFS loudness measurement
"""

import warnings
from typing import Dict, Optional, Tuple

try:
    import essentia.standard as es

    _ESSENTIA_AVAILABLE = True
except Exception:
    es = None
    _ESSENTIA_AVAILABLE = False
import numpy as np
import parselmouth
import pyloudnorm as pyln
import soundfile as sf
import torch
import torchaudio
import torchaudio.transforms as T
from parselmouth.praat import call

warnings.filterwarnings("ignore")


class AdvancedVocalAnalyzer:
    """
    고급 4축 보컬 분석기
    """

    def __init__(self, sample_rate: int = 22050):
        self.sr = sample_rate
        self.setup_processors()

    def setup_processors(self):
        """각 라이브러리별 프로세서 초기화"""

        # Torchaudio transforms (GPU 가속)
        self.mel_transform = T.MelSpectrogram(
            sample_rate=self.sr, n_fft=2048, n_mels=128
        )

        # Essentia-based processors when available
        if _ESSENTIA_AVAILABLE and es is not None:
            try:
                self.windowing = es.Windowing(type="hann")
                self.spectrum = es.Spectrum()
                self.spectral_centroid = es.SpectralCentroid()
                self.spectral_rolloff = es.SpectralRollOff()
                self.harmonic_peaks = es.HarmonicPeaks()
                self.spectral_complexity = es.SpectralComplexity()
            except Exception:
                # If essentia initialization fails at runtime, disable essentia usage
                self.windowing = None
                self.spectrum = None
                self.spectral_centroid = None
                self.spectral_rolloff = None
                self.harmonic_peaks = None
                self.spectral_complexity = None
                # Safely mark module-level flag without using 'global' in nested scope
                globals()["_ESSENTIA_AVAILABLE"] = False
        else:
            # Ensure attributes exist even when essentia is not available
            self.windowing = None
            self.spectrum = None
            self.spectral_centroid = None
            self.spectral_rolloff = None
            self.harmonic_peaks = None
            self.spectral_complexity = None

        # Loudness meter
        self.loudness_meter = pyln.Meter(self.sr)

    def analyze_audio(self, audio_data: bytes) -> Dict[str, float]:
        """
        4축 보컬 분석 메인 함수
        """
        # If essentia is not available at import/runtime, delegate to the no-essentia analyzer
        if not _ESSENTIA_AVAILABLE:
            try:
                from advanced_vocal_analyzer_no_essentia import \
                    AdvancedVocalAnalyzerNoEssentia as _NoEssentiaAnalyzer

                analyzer = _NoEssentiaAnalyzer(sample_rate=self.sr)
                return analyzer.analyze_audio(audio_data)
            except Exception:
                # fall through to try the local implementation and return fallback on failure
                pass

        try:
            # 오디오 로드 및 전처리
            audio = self._load_and_preprocess(audio_data)

            # 4축 분석 수행
            brightness = self._analyze_brightness(audio)
            thickness = self._analyze_thickness(audio)
            adduction = self._analyze_adduction(audio)
            spl = self._analyze_spl(audio)

            # 성별 추론 및 잠재적 고음력 계산
            gender = self._infer_gender(brightness, thickness, spl, audio)
            potential_high_note = self._calculate_potential_high_note(
                gender, brightness, thickness, adduction, spl
            )

            return {
                "brightness": float(brightness),
                "thickness": float(thickness),
                "adduction": float(adduction),
                "spl": float(spl),
                "gender": gender,
                "potential_high_note": potential_high_note,
            }

        except Exception as e:
            print(f"Analysis error: {e}")
            return self._get_fallback_scores()

    def _load_and_preprocess(self, audio_data: bytes) -> np.ndarray:
        """오디오 데이터 로드 및 전처리"""

        # BytesIO로 변환하여 soundfile로 로드
        import io

        audio_buffer = io.BytesIO(audio_data)
        audio, sr = sf.read(audio_buffer)

        # 모노 변환
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # 리샘플링 (필요시)
        if sr != self.sr:
            import resampy

            audio = resampy.resample(audio, sr, self.sr)

        # 정규화 및 무음 제거
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        audio = self._trim_silence(audio)

        return audio

    def _trim_silence(self, audio: np.ndarray, top_db: int = 20) -> np.ndarray:
        """무음 구간 제거"""
        # 간단한 에너지 기반 트리밍
        frame_length = 2048
        hop_length = 512

        energy = np.array(
            [
                sum(abs(audio[i : i + frame_length] ** 2))
                for i in range(0, len(audio) - frame_length, hop_length)
            ]
        )

        # 임계값 계산
        energy_db = 20 * np.log10(energy + 1e-8)
        threshold = np.max(energy_db) - top_db

        # 유효한 프레임 찾기
        valid_frames = energy_db > threshold
        if not np.any(valid_frames):
            return audio

        start_frame = np.where(valid_frames)[0][0] * hop_length
        end_frame = (np.where(valid_frames)[0][-1] + 1) * hop_length

        return audio[start_frame : min(end_frame, len(audio))]

    def _analyze_brightness(self, audio: np.ndarray) -> float:
        """
        밝기 분석: Spectral centroid + Formant analysis
        Range: -100 (어두움) ~ +100 (밝음)
        """
        try:
            # 1. Essentia - Spectral Centroid
            windowed = self.windowing(audio.astype(np.float32))
            spectrum = self.spectrum(windowed)
            centroid = self.spectral_centroid(spectrum)

            # 2. Praat - Formant Analysis
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
            formant = sound.to_formant_burg()

            # F1, F2 추출 (중간 지점에서)
            duration = sound.duration
            mid_time = duration / 2

            try:
                f1 = call(formant, "Get value at time", 1, mid_time, "Hertz", "Linear")
                f2 = call(formant, "Get value at time", 2, mid_time, "Hertz", "Linear")

                # F2/F1 비율로 밝기 계산 (높을수록 밝음)
                if f1 > 0 and f2 > 0:
                    formant_brightness = (f2 / f1 - 1.5) * 50  # 정규화
                else:
                    formant_brightness = 0
            except:
                formant_brightness = 0

            # Spectral centroid 정규화 (1000-4000Hz 기준)
            spectral_brightness = (centroid - 2500) / 25

            # 가중 평균
            brightness = 0.6 * spectral_brightness + 0.4 * formant_brightness

            return np.clip(brightness, -100, 100)

        except Exception as e:
            print(f"Brightness analysis error: {e}")
            return 0.0

    def _analyze_thickness(self, audio: np.ndarray) -> float:
        """
        음색 두께 분석: Harmonic richness + Spectral complexity
        Range: -100 (얇음) ~ +100 (두꺼움)
        """
        try:
            # 1. Harmonic analysis with Essentia
            windowed = self.windowing(audio.astype(np.float32))
            spectrum = self.spectrum(windowed)

            # Harmonic peaks 추출
            frequencies, magnitudes = self.harmonic_peaks(spectrum)

            # Harmonic richness (배음 개수와 강도)
            if len(frequencies) > 1:
                # 기본 주파수 대비 배음들의 에너지 비율
                harmonic_energy = np.sum(magnitudes[1:]) / (magnitudes[0] + 1e-8)
                harmonic_richness = min(harmonic_energy * 20, 50)  # 정규화
            else:
                harmonic_richness = 0

            # 2. Spectral complexity
            complexity = self.spectral_complexity(spectrum)
            spectral_thickness = (complexity - 0.5) * 100

            # 3. Mel spectrogram energy distribution (Torchaudio)
            audio_tensor = torch.FloatTensor(audio)
            mel_spec = self.mel_transform(audio_tensor)

            # 저주파 대역 에너지 비율 (두꺼운 느낌)
            low_freq_energy = torch.mean(mel_spec[:32, :])  # 저주파 32 빈
            high_freq_energy = torch.mean(mel_spec[64:, :])  # 고주파 빈

            freq_balance = (low_freq_energy - high_freq_energy) * 10

            # 가중 평균
            thickness = (
                0.4 * harmonic_richness + 0.3 * spectral_thickness + 0.3 * freq_balance
            )

            return float(np.clip(thickness, -100, 100))

        except Exception as e:
            print(f"Thickness analysis error: {e}")
            return 0.0

    def _analyze_adduction(self, audio: np.ndarray) -> float:
        """
        성대 내전 정도 분석: HNR + Jitter/Shimmer
        Range: -100 (불완전한 내전) ~ +100 (완전한 내전)
        """
        try:
            # Praat을 사용한 음성학적 분석
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)

            # 1. HNR (Harmonic-to-Noise Ratio)
            harmonicity = sound.to_harmonicity()
            hnr_values = harmonicity.values
            hnr_mean = np.mean(hnr_values[~np.isnan(hnr_values)])

            # HNR 점수 (10dB 이상이 좋음)
            hnr_score = min((hnr_mean - 5) * 10, 50)  # -50 ~ +50

            # 2. Jitter (음높이 불안정성)
            try:
                pitch = sound.to_pitch()
                jitter_local = call(
                    pitch, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3
                )
                jitter_score = max(50 - jitter_local * 1000, -50)  # 낮을수록 좋음
            except:
                jitter_score = 0

            # 3. Shimmer (진폭 불안정성)
            try:
                shimmer_local = call(
                    sound, "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
                )
                shimmer_score = max(50 - shimmer_local * 100, -50)  # 낮을수록 좋음
            except:
                shimmer_score = 0

            # 4. Voice breaks 감지 (추가 지표)
            # 급격한 진폭 변화 감지
            rms_frames = []
            frame_size = int(0.025 * self.sr)  # 25ms frames
            hop_size = int(0.010 * self.sr)  # 10ms hop

            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i : i + frame_size]
                rms_frames.append(np.sqrt(np.mean(frame**2)))

            rms_frames = np.array(rms_frames)
            rms_variation = np.std(rms_frames) / (np.mean(rms_frames) + 1e-8)
            voice_stability = max(50 - rms_variation * 100, -50)

            # 가중 평균 (HNR이 가장 중요)
            adduction = (
                0.5 * hnr_score
                + 0.2 * jitter_score
                + 0.2 * shimmer_score
                + 0.1 * voice_stability
            )

            return float(np.clip(adduction, -100, 100))

        except Exception as e:
            print(f"Adduction analysis error: {e}")
            return 0.0

    def _analyze_spl(self, audio: np.ndarray) -> float:
        """
        음압/소리 세기 분석: RMS + LUFS
        Range: -100 (약함) ~ +100 (강함)
        """
        try:
            # 1. RMS Energy
            rms_energy = np.sqrt(np.mean(audio**2))
            rms_db = 20 * np.log10(rms_energy + 1e-8)

            # RMS 정규화 (-60dB ~ 0dB 기준)
            rms_score = (rms_db + 60) * 100 / 60

            # 2. LUFS (Loudness Units Full Scale)
            try:
                # 최소 길이 확인 (LUFS 측정을 위해)
                if len(audio) / self.sr >= 0.4:  # 0.4초 이상
                    lufs = self.loudness_meter.integrated_loudness(audio)
                    # LUFS 정규화 (-50 LUFS ~ -10 LUFS 기준)
                    lufs_score = (lufs + 50) * 100 / 40
                else:
                    lufs_score = rms_score  # 짧은 오디오는 RMS 사용
            except:
                lufs_score = rms_score

            # 3. Dynamic Range
            peak_level = 20 * np.log10(np.max(np.abs(audio)) + 1e-8)
            dynamic_range = peak_level - rms_db
            dynamic_score = min(dynamic_range * 5, 50)  # 넓은 다이나믹 레인지 보너스

            # 가중 평균
            spl = 0.6 * rms_score + 0.3 * lufs_score + 0.1 * dynamic_score

            return float(np.clip(spl, -100, 100))

        except Exception as e:
            print(f"SPL analysis error: {e}")
            return 0.0

    def _infer_gender(
        self, brightness: float, thickness: float, spl: float, audio: np.ndarray
    ) -> str:
        """성별 추론"""
        try:
            # Praat으로 기본 주파수 추출
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
            pitch = sound.to_pitch()
            f0_values = pitch.selected_array["frequency"]
            f0_values = f0_values[f0_values != 0]  # 무음 구간 제거

            if len(f0_values) > 0:
                avg_f0 = np.mean(f0_values)

                # 기본 주파수 기반 성별 판단
                if avg_f0 > 180:  # 180Hz 이상은 일반적으로 여성
                    return "female"
                elif avg_f0 < 130:  # 130Hz 이하는 일반적으로 남성
                    return "male"
                else:
                    # 애매한 경우 4축 데이터로 보완
                    gender_score = 0
                    if brightness > 10:
                        gender_score += 1
                    if thickness < 0:
                        gender_score += 1
                    if spl < 20:
                        gender_score += 1
                    return "female" if gender_score >= 2 else "male"
            else:
                # F0 추출 실패시 4축 데이터만으로 판단
                gender_score = 0
                if brightness > 10:
                    gender_score += 1
                if thickness < 0:
                    gender_score += 1
                if spl < 20:
                    gender_score += 1
                return "female" if gender_score >= 2 else "male"

        except:
            return "unknown"

    def _calculate_potential_high_note(
        self,
        gender: str,
        brightness: float,
        thickness: float,
        adduction: float,
        spl: float,
    ) -> str:
        """성별별 잠재적 고음력 계산 (대중가요 기준)"""

        # 대중가요 기준 잠재적 고음 범위
        if gender == "male":
            # 남성 대중가요: A4 ~ F5 범위 (더 높게 설정)
            # 예: 임재범 F5, 김범수 F#5, 나얼 F5, 박효신 G5
            base_notes = ["A4", "A#4", "B4", "C5", "C#5", "D5", "D#5", "E5", "F5"]
            base_idx = 4  # C#5 기준 (대중가요 남성 평균)
        elif gender == "female":
            # 여성 대중가요: C5 ~ A5 범위 (실용적 범위)
            # 예: 이소라 F#5, 백지영 G5, 소향 A5+, 태연 G#5
            base_notes = [
                "C5",
                "C#5",
                "D5",
                "D#5",
                "E5",
                "F5",
                "F#5",
                "G5",
                "G#5",
                "A5",
            ]
            base_idx = 5  # F5 기준 (대중가요 여성 평균)
        else:
            return "E5"  # 중간값

        # 4축 점수로 보정 계산
        adjustment = 0

        # 밝기: 밝을수록 고음에 유리 (대중가요에서 중요)
        if brightness > 50:
            adjustment += 3
        elif brightness > 20:
            adjustment += 2
        elif brightness > 0:
            adjustment += 1
        elif brightness < -40:
            adjustment -= 2

        # 두께: 대중가요에서는 적당한 두께가 유리
        if -10 <= thickness <= 20:  # 적당한 두께
            adjustment += 1
        elif thickness < -30:  # 너무 얇으면
            adjustment += 2  # 고음에 더 유리
        elif thickness > 50:  # 너무 두꺼우면
            adjustment -= 2

        # 성대 내전: 대중가요 고음에 가장 중요
        if adduction > 60:
            adjustment += 3  # 매우 중요
        elif adduction > 30:
            adjustment += 2
        elif adduction > 0:
            adjustment += 1
        elif adduction < -30:
            adjustment -= 2

        # SPL: 대중가요는 적절한 파워 필요
        if 30 <= spl <= 70:  # 최적 범위
            adjustment += 1
        elif spl > 80:  # 너무 강하면 고음 제어 어려움
            adjustment -= 1
        elif spl < 10:  # 너무 약하면 고음 힘 부족
            adjustment -= 1

        # 보정값 적용 (범위 확장)
        final_idx = max(0, min(len(base_notes) - 1, base_idx + adjustment))

        return base_notes[final_idx]

    def _get_fallback_scores(self) -> Dict[str, float]:
        """분석 실패시 기본값 반환"""
        return {
            "brightness": 0.0,
            "thickness": 0.0,
            "adduction": 0.0,
            "spl": 0.0,
            "gender": "unknown",
            "potential_high_note": "E5",
        }


# 사용 예시
if __name__ == "__main__":
    analyzer = AdvancedVocalAnalyzer()

    # 테스트용 더미 데이터
    import io

    test_audio = np.random.randn(44100) * 0.1  # 1초 더미 오디오
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, test_audio, 22050, format="wav")

    results = analyzer.analyze_audio(audio_buffer.getvalue())
    print("4축 보컬 분석 결과:")
    print(f"밝기 (Brightness): {results['brightness']:.1f}")
    print(f"두께 (Thickness): {results['thickness']:.1f}")
    print(f"성대내전 (Adduction): {results['adduction']:.1f}")
    print(f"음압 (SPL): {results['spl']:.1f}")
