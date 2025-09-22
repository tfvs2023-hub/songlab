"""
Phone Recording Simulator
스튜디오 녹음을 폰 녹음처럼 변환하는 파이프라인
"""

import random
from typing import Optional, Tuple

import numpy as np
import pyloudnorm as pyln
import scipy.signal as signal
import soundfile as sf


class PhoneSimulator:
    """
    폰 녹음 시뮬레이터
    디바이스 IR, AGC, 코덱, 리버브, 노이즈 적용
    """

    def __init__(self, sample_rate: int = 16000):
        self.sr = sample_rate
        self.meter = pyln.Meter(self.sr)

    def simulate(
        self,
        audio: np.ndarray,
        sr_orig: int,
        snr_db: float = None,
        codec: str = "opus",
        device: str = "generic",
    ) -> np.ndarray:
        """
        폰 녹음 시뮬레이션 메인 함수
        """
        # 1. Loudness normalization to -23 LUFS
        audio = self._normalize_loudness(audio, -23.0)

        # 2. Resample to 16k if needed
        if sr_orig != self.sr:
            import resampy

            audio = resampy.resample(audio, sr_orig, self.sr)

        # 3. Bandpass filter 80-8000 Hz (폰 주파수 대역)
        audio = self._bandpass_filter(audio, 80, 8000)

        # 4. Pre-emphasis 0.97
        audio = self._apply_preemphasis(audio, 0.97)

        # 5. Device IR convolution (폰 마이크 특성)
        audio = self._apply_device_ir(audio, device)

        # 6. AGC simulation (자동 게인 조절)
        audio = self._simulate_agc(audio)

        # 7. Codec simulation (압축 손실)
        audio = self._simulate_codec(audio, codec)

        # 8. Small room reverb (약간의 공간감)
        audio = self._add_room_reverb(audio, mix=0.1)

        # 9. Environmental noise (환경 소음)
        if snr_db is None:
            snr_db = random.uniform(20, 35)  # 20-35 dB SNR
        audio = self._add_noise(audio, snr_db)

        # 10. Final normalization
        audio = self._normalize_loudness(audio, -23.0)

        return audio

    def _normalize_loudness(self, audio: np.ndarray, target_lufs: float) -> np.ndarray:
        """LUFS 정규화"""
        try:
            loudness = self.meter.integrated_loudness(audio)
            if not np.isnan(loudness) and not np.isinf(loudness):
                return pyln.normalize.loudness(audio, loudness, target_lufs)
        except:
            pass
        return audio

    def _bandpass_filter(
        self, audio: np.ndarray, low_freq: int, high_freq: int
    ) -> np.ndarray:
        """대역통과 필터"""
        sos = signal.butter(
            4, [low_freq, high_freq], btype="band", fs=self.sr, output="sos"
        )
        return signal.sosfilt(sos, audio)

    def _apply_preemphasis(self, audio: np.ndarray, coef: float) -> np.ndarray:
        """Pre-emphasis 필터"""
        return np.append(audio[0], audio[1:] - coef * audio[:-1])

    def _apply_device_ir(self, audio: np.ndarray, device: str) -> np.ndarray:
        """
        디바이스 IR (Impulse Response) 적용
        실제로는 측정된 IR을 사용하지만, 여기서는 간단한 필터로 시뮬레이션
        """
        if device == "iphone":
            # iPhone 특성: 중음역 부스트, 저음 컷
            sos = signal.butter(2, [200, 6000], btype="band", fs=self.sr, output="sos")
            audio = signal.sosfilt(sos, audio)
            # 2-4kHz 부스트
            sos_boost = signal.butter(
                2, [2000, 4000], btype="band", fs=self.sr, output="sos"
            )
            boost = signal.sosfilt(sos_boost, audio)
            audio = audio + 0.3 * boost

        elif device == "android":
            # Android 특성: 더 넓은 대역, 약간의 저음
            sos = signal.butter(2, [150, 7000], btype="band", fs=self.sr, output="sos")
            audio = signal.sosfilt(sos, audio)

        else:  # generic
            # 일반적인 폰 마이크 특성
            sos = signal.butter(2, [180, 6500], btype="band", fs=self.sr, output="sos")
            audio = signal.sosfilt(sos, audio)

        return audio

    def _simulate_agc(
        self,
        audio: np.ndarray,
        target_level: float = 0.3,
        attack_time: float = 0.01,
        release_time: float = 0.1,
    ) -> np.ndarray:
        """
        AGC (Automatic Gain Control) 시뮬레이션
        폰에서 자동으로 레벨을 조절하는 효과
        """
        # Simple envelope follower
        frame_size = int(0.01 * self.sr)  # 10ms frames
        envelope = []

        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i : i + frame_size]
            envelope.append(np.sqrt(np.mean(frame**2)))

        if not envelope:
            return audio

        # Smooth envelope
        from scipy.ndimage import uniform_filter1d

        envelope = uniform_filter1d(envelope, size=5, mode="nearest")

        # Calculate gain
        gains = []
        for env in envelope:
            if env > 0:
                gain = target_level / (env + 1e-10)
                gain = np.clip(gain, 0.5, 2.0)  # Limit gain range
            else:
                gain = 1.0
            gains.append(gain)

        # Interpolate gains to audio length
        gain_curve = np.interp(
            np.arange(len(audio)), np.linspace(0, len(audio), len(gains)), gains
        )

        # Apply smooth gain
        return audio * gain_curve

    def _simulate_codec(self, audio: np.ndarray, codec: str) -> np.ndarray:
        """
        코덱 시뮬레이션 (손실 압축)
        실제로는 ffmpeg를 통해 인코딩/디코딩하지만
        여기서는 간단한 시뮬레이션
        """
        if codec == "opus":
            # Opus 16-32kbps 시뮬레이션
            # 고주파 손실 + 양자화 노이즈
            cutoff = random.uniform(6000, 7000)
            sos = signal.butter(4, cutoff, btype="low", fs=self.sr, output="sos")
            audio = signal.sosfilt(sos, audio)
            # Quantization noise
            quant_levels = 2**12  # 12-bit
            audio = np.round(audio * quant_levels) / quant_levels

        elif codec == "aac":
            # AAC 64-96kbps 시뮬레이션
            cutoff = random.uniform(7000, 7500)
            sos = signal.butter(4, cutoff, btype="low", fs=self.sr, output="sos")
            audio = signal.sosfilt(sos, audio)
            # Less quantization noise
            quant_levels = 2**14  # 14-bit
            audio = np.round(audio * quant_levels) / quant_levels

        elif codec == "amr":
            # AMR (전화 품질) 시뮬레이션
            # 더 심한 대역 제한
            sos = signal.butter(4, [300, 3400], btype="band", fs=self.sr, output="sos")
            audio = signal.sosfilt(sos, audio)
            # Heavy quantization
            quant_levels = 2**8  # 8-bit
            audio = np.round(audio * quant_levels) / quant_levels

        return audio

    def _add_room_reverb(
        self, audio: np.ndarray, room_size: float = 0.3, mix: float = 0.1
    ) -> np.ndarray:
        """
        간단한 룸 리버브 추가
        Schroeder reverb 알고리즘의 간소화 버전
        """
        # Comb filters (parallel)
        delays_ms = [29.7, 37.1, 41.1, 43.7]  # in ms
        decays = [0.8, 0.75, 0.73, 0.71]

        reverb = np.zeros_like(audio)

        for delay_ms, decay in zip(delays_ms, decays):
            delay_samples = int(delay_ms * self.sr / 1000 * room_size)
            if delay_samples < len(audio):
                # Simple comb filter
                delayed = np.zeros_like(audio)
                delayed[delay_samples:] = audio[:-delay_samples] * decay

                # Feedback
                for _ in range(3):
                    temp = np.zeros_like(delayed)
                    temp[delay_samples:] = delayed[:-delay_samples] * decay
                    delayed = delayed + temp * 0.5

                reverb += delayed

        # Mix dry and wet
        return audio * (1 - mix) + reverb * mix / len(delays_ms)

    def _add_noise(self, audio: np.ndarray, snr_db: float) -> np.ndarray:
        """
        환경 소음 추가
        다양한 노이즈 타입 중 랜덤 선택
        """
        noise_type = random.choice(["white", "pink", "brown", "office", "street"])

        if noise_type == "white":
            noise = np.random.normal(0, 1, len(audio))

        elif noise_type == "pink":
            # Pink noise (1/f)
            white = np.random.normal(0, 1, len(audio))
            # Simple pink noise approximation
            b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
            a = [1, -2.494956002, 2.017265875, -0.522189400]
            noise = signal.lfilter(b, a, white)

        elif noise_type == "brown":
            # Brown noise (1/f^2)
            white = np.random.normal(0, 1, len(audio))
            noise = np.cumsum(white) / 100

        elif noise_type == "office":
            # Office ambiente: 주로 저주파 + 간헐적 중주파
            brown = np.cumsum(np.random.normal(0, 1, len(audio))) / 100
            pink = signal.lfilter(
                [0.05, -0.095, 0.05], [1, -2.5, 2.0], np.random.normal(0, 1, len(audio))
            )
            noise = 0.7 * brown + 0.3 * pink
            # Add some sporadic mid-freq
            if random.random() > 0.5:
                burst_pos = random.randint(0, len(audio) - self.sr)
                burst_len = random.randint(int(0.1 * self.sr), int(0.5 * self.sr))
                noise[burst_pos : burst_pos + burst_len] += np.random.normal(
                    0, 0.3, burst_len
                )

        else:  # street
            # Street noise: 광대역 + 저주파 럼블
            white = np.random.normal(0, 1, len(audio))
            rumble = signal.butter(2, 200, btype="low", fs=self.sr, output="sos")
            low_rumble = signal.sosfilt(rumble, white) * 2
            noise = white * 0.3 + low_rumble * 0.7

        # Normalize noise
        noise = noise / (np.std(noise) + 1e-10)

        # Calculate signal and noise power
        signal_power = np.mean(audio**2)
        noise_power = np.mean(noise**2)

        # Calculate noise scaling factor for target SNR
        snr_linear = 10 ** (snr_db / 10)
        noise_scale = np.sqrt(signal_power / (snr_linear * noise_power + 1e-10))

        # Add scaled noise
        return audio + noise * noise_scale


class PhoneDataAugmentor:
    """
    학습 데이터 증강을 위한 폰 시뮬레이션 파이프라인
    """

    def __init__(self):
        self.simulator = PhoneSimulator()

    def augment_batch(self, audio_files: list, output_dir: str):
        """
        배치 처리로 폰 시뮬레이션 적용
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        augmented_files = []

        for audio_file in audio_files:
            try:
                # Load audio
                audio, sr = sf.read(audio_file)

                # Multiple augmentations per file
                augmentations = [
                    {"snr": 35, "codec": "opus", "device": "iphone"},
                    {"snr": 25, "codec": "aac", "device": "android"},
                    {"snr": 20, "codec": "opus", "device": "generic"},
                    {"snr": 30, "codec": "amr", "device": "generic"},  # 전화 품질
                ]

                for i, aug_params in enumerate(augmentations):
                    # Apply simulation
                    augmented = self.simulator.simulate(
                        audio,
                        sr,
                        snr_db=aug_params["snr"],
                        codec=aug_params["codec"],
                        device=aug_params["device"],
                    )

                    # Save augmented file
                    base_name = os.path.splitext(os.path.basename(audio_file))[0]
                    output_file = os.path.join(
                        output_dir,
                        f"{base_name}_phone_snr{aug_params['snr']}_{aug_params['codec']}_{aug_params['device']}.wav",
                    )

                    sf.write(output_file, augmented, 16000)
                    augmented_files.append(output_file)

            except Exception as e:
                print(f"Error processing {audio_file}: {e}")
                continue

        return augmented_files
