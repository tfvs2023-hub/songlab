import numpy as np
import librosa
import crepe
from scipy import signal
from scipy.stats import skew, kurtosis
import io
import soundfile as sf
from pydub import AudioSegment
import tempfile
import os

class VoiceAnalyzer:
    def __init__(self):
        self.sr = 16000  # CREPE works best at 16kHz
        
    def analyze_audio(self, audio_data):
        """
        Main analysis function that returns 4-axis scores
        """
        try:
            # Try to load audio directly first
            audio, sr = sf.read(io.BytesIO(audio_data))
        except:
            # If direct loading fails, try converting with pydub
            try:
                # Convert to wav using pydub for better compatibility
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
                
                # Convert to wav format
                wav_io = io.BytesIO()
                audio_segment.export(wav_io, format="wav")
                wav_io.seek(0)
                
                # Now load the wav
                audio, sr = sf.read(wav_io)
            except Exception as e:
                raise Exception(f"Failed to load audio file: {str(e)}")
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
            
        # Resample to 16kHz for CREPE
        if sr != self.sr:
            audio = librosa.resample(y=audio, orig_sr=sr, target_sr=self.sr)
            
        # Get pitch using CREPE (using 'tiny' model for faster processing)
        time, frequency, confidence, activation = crepe.predict(
            audio, self.sr, viterbi=True, model_capacity='tiny', step_size=50
        )
        
        # Filter out low confidence predictions
        valid_freq = frequency[confidence > 0.5]
        
        # Calculate 4-axis scores
        brightness = self._calculate_brightness(audio, self.sr, valid_freq)
        thickness = self._calculate_thickness(audio, self.sr)
        clarity = self._calculate_clarity(audio, self.sr, confidence)
        power = self._calculate_power(audio)
        
        # 성별 추정 및 고음 잠재력 계산
        gender = self._infer_gender(brightness, thickness, power, audio)
        potential_high_note = self._calculate_potential_high_note(gender, brightness, thickness, clarity, power)
        
        return {
            "brightness": brightness,
            "thickness": thickness,
            "clarity": clarity,
            "power": power,
            "potential_high_note": potential_high_note,
            "gender": gender
        }
    
    def _calculate_brightness(self, audio, sr, pitch_freq):
        """
        Calculate brightness based on formant frequencies and spectral centroid
        Higher formants = brighter voice
        """
        # Spectral centroid (center of mass of spectrum)
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        mean_centroid = np.mean(spectral_centroids)
        
        # Check for NaN values
        if np.isnan(mean_centroid):
            mean_centroid = 1500  # Default value
        
        # Normalize to human voice range (typically 100-4000 Hz for speaking)
        # Map to -100 to +100
        # Female voices typically have higher centroids (brighter)
        normalized = (mean_centroid - 1500) / 1500  # Center around 1500 Hz
        brightness_score = np.clip(normalized * 100, -100, 100)
        
        # Adjust based on pitch variance (more variance = potentially brighter)
        if len(pitch_freq) > 0:
            pitch_std = np.std(pitch_freq)
            if not np.isnan(pitch_std):
                brightness_score += np.clip(pitch_std / 10, -20, 20)
        
        # Final NaN check
        if np.isnan(brightness_score):
            brightness_score = 0
            
        return float(np.clip(brightness_score, -100, 100))
    
    def _calculate_thickness(self, audio, sr):
        """
        Calculate thickness based on low/high frequency ratio
        More low frequencies = thicker voice
        """
        # Get frequency spectrum
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1/sr)
        magnitude = np.abs(fft)
        
        # Define frequency bands
        low_band = (freqs >= 80) & (freqs <= 500)  # Low frequencies
        high_band = (freqs >= 2000) & (freqs <= 4000)  # High frequencies
        
        # Calculate energy ratio
        low_energy = np.sum(magnitude[low_band] ** 2)
        high_energy = np.sum(magnitude[high_band] ** 2)
        
        if high_energy > 0:
            ratio = low_energy / high_energy
            # More low freq = positive score (thicker)
            # More high freq = negative score (thinner)
            thickness_score = (np.log10(ratio + 0.1) * 50)
        else:
            thickness_score = 50
        
        # Check for NaN values
        if np.isnan(thickness_score):
            thickness_score = 0
            
        return float(np.clip(thickness_score, -100, 100))
    
    def _calculate_clarity(self, audio, sr, confidence):
        """
        Calculate clarity based on pitch confidence and spectral features
        Higher confidence and less noise = clearer voice (better vocal fold closure)
        """
        # Mean pitch confidence
        mean_confidence = np.mean(confidence)
        
        # Zero crossing rate (indicator of noise vs tonal content)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        mean_zcr = np.mean(zcr)
        
        # Spectral rolloff (frequency below which 85% of energy is contained)
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.85)[0]
        mean_rolloff = np.mean(rolloff)
        
        # Check for NaN values
        if np.isnan(mean_confidence):
            mean_confidence = 0.5
        if np.isnan(mean_zcr):
            mean_zcr = 0.1
        if np.isnan(mean_rolloff):
            mean_rolloff = 2000
        
        # Combine metrics
        # High confidence + low ZCR + moderate rolloff = clear voice
        clarity_score = (mean_confidence * 100) - (mean_zcr * 1000) + (mean_rolloff / 50)
        
        # Normalize to -100 to +100
        clarity_score = (clarity_score - 50) * 2
        
        # Final NaN check
        if np.isnan(clarity_score):
            clarity_score = 0
        
        return float(np.clip(clarity_score, -100, 100))
    
    def _calculate_power(self, audio):
        """
        Calculate power based on RMS energy
        Higher RMS = more powerful voice
        """
        # Calculate RMS
        rms = np.sqrt(np.mean(audio ** 2))
        
        # Convert to dB
        db = 20 * np.log10(rms + 1e-10)
        
        # Check for NaN values
        if np.isnan(rms) or np.isnan(db):
            power_score = -50  # Default value for low power
        else:
            # Normalize to -100 to +100
            # Typical speaking voice is around -20 to -10 dB
            # Map -40 dB to -100, -10 dB to +100
            power_score = ((db + 40) / 30) * 200 - 100
        
        # Final NaN check
        if np.isnan(power_score):
            power_score = -50
        
        return float(np.clip(power_score, -100, 100))
    
    def generate_mbti_style(self, scores):
        """
        Generate voice type classification based on 4-axis scores
        """
        # Map scores to voice characteristic dimensions
        type_code = ""
        
        # Brightness: B (Bright) vs D (Dark)
        type_code += "B" if scores["brightness"] > 0 else "D"
        
        # Thickness: T (Thick) vs N (thiN)  
        type_code += "T" if scores["thickness"] > 0 else "N"
        
        # Clarity: C (Clear) vs F (Foggy/breathy)
        type_code += "C" if scores["clarity"] > 0 else "F"
        
        # Power: P (Powerful) vs S (Soft)
        type_code += "P" if scores["power"] > 0 else "S"
        
        # Define characteristics for each type
        voice_descriptions = {
            "BTCP": "밝고 두꺼우며 명료하고 파워풀한 보컬 | 팝/뮤지컬형",
            "BTCS": "밝고 두껍고 명료하지만 부드러운 보컬 | 팝/발라드형",
            "BTFP": "밝고 두껍고 숨섞인 파워풀한 보컬 | 소울/블루스형",
            "BTFS": "밝고 두껍고 숨섞인 부드러운 보컬 | R&B/네오소울형",
            "BNCP": "밝고 얇으며 명료하고 파워풀한 보컬 | K-POP/댄스형",
            "BNCS": "밝고 얇고 명료하지만 부드러운 보컬 | 어쿠스틱/포크형",
            "BNFP": "밝고 얇고 숨섞인 파워풀한 보컬 | 인디팝/드림팝형",
            "BNFS": "밝고 얇고 숨섞인 부드러운 보컬 | 보사노바/재즈형",
            "DTCP": "어둡고 두꺼우며 명료하고 파워풀한 보컬 | 록/메탈형",
            "DTCS": "어둡고 두껍고 명료하지만 부드러운 보컬 | 컨트리/블루스형",
            "DTFP": "어둡고 두껍고 숨섞인 파워풀한 보컬 | 힙합/트랩형",
            "DTFS": "어둡고 두껍고 숨섞인 부드러운 보컬 | 재즈/소울형",
            "DNCP": "어둡고 얇으며 명료하고 파워풀한 보컬 | 얼터너티브/인디록형",
            "DNCS": "어둡고 얇고 명료하지만 부드러운 보컬 | 싱어송라이터/포크형",
            "DNFP": "어둡고 얇고 숨섞인 파워풀한 보컬 | 일렉트로닉/신스팝형",
            "DNFS": "어둡고 얇고 숨섞인 부드러운 보컬 | Lo-Fi/칠아웃형"
        }
        
        # Generate training keywords based on lowest score
        # Filter out non-numeric values first
        numeric_scores = {k: v for k, v in scores.items() if isinstance(v, (int, float))}
        lowest_axis = min(numeric_scores, key=numeric_scores.get) if numeric_scores else 'brightness'
        
        keyword_map = {
            "brightness": ["포먼트 조절 보컬 레슨", "공명 훈련 발성법", "밝은 음색 만들기"],
            "thickness": ["성구 전환 연습법", "믹스 보이스 훈련", "음색 두께 조절법"],
            "clarity": ["성대 내전 발성법", "명료한 발음 훈련", "깨끗한 음색 만들기"],
            "power": ["복식 호흡법", "음압 조절 훈련", "파워풀한 발성법"]
        }
        
        return {
            "typeCode": type_code,
            "typeName": type_code,
            "typeIcon": self._get_type_icon(type_code),
            "description": voice_descriptions.get(type_code, "독특한 개성의 보컬"),
            "scores": scores,
            "youtubeKeywords": keyword_map.get(lowest_axis, ["보컬 기초 발성법"])
        }
    
    def _get_type_icon(self, type_code):
        """
        Return emoji icon based on voice type
        """
        icon_map = {
            "B": "🌟", "D": "🌙",  # Bright vs Dark
            "T": "🎸", "N": "🎹",  # Thick vs thiN
            "C": "🎯", "F": "💫",  # Clear vs Foggy
            "P": "⚡", "S": "🌊"   # Powerful vs Soft
        }
        # Return icon based on first letter (B/D)
        return icon_map.get(type_code[0], "🎤")
    
    def _infer_gender(self, brightness: float, thickness: float, spl: float, audio: np.ndarray) -> str:
        """성별 추론"""
        try:
            # 평균 주파수 계산
            mean_freq = np.mean(librosa.fft_frequencies(sr=self.sr, n_fft=2048))
            
            # 성별 판단 기준
            if mean_freq > 150:  # 여성 범위
                gender_score = 0
                if brightness > 10: gender_score += 1
                if thickness < 0: gender_score += 1
                if spl < 20: gender_score += 1
                return 'female' if gender_score >= 2 else 'male'
            else:
                return 'unknown'
                
        except:
            return 'unknown'
    
    def _calculate_potential_high_note(self, gender: str, brightness: float, thickness: float, clarity: float, spl: float) -> str:
        """잠재적 고음력 계산"""
        
        if gender == 'male':
            base_notes = ['A4', 'A#4', 'B4', 'C5', 'C#5', 'D5', 'D#5', 'E5', 'F5']
            base_idx = 4  # C#5
        elif gender == 'female':
            base_notes = ['C5', 'C#5', 'D5', 'D#5', 'E5', 'F5', 'F#5', 'G5', 'G#5', 'A5']
            base_idx = 5  # F5
        else:
            return 'E5'
        
        # 음성 특성 점수 계산
        score_adjustment = 0
        
        # 밝기 (음색 밝기가 높을수록 고음 유리)
        score_adjustment += int(brightness / 30)
        
        # 두께 (적당한 두께가 고음에 유리)
        if -20 <= thickness <= 20:
            score_adjustment += 1
        elif thickness > 50:
            score_adjustment -= 1
            
        # 명료도 (높을수록 고음 유리)
        score_adjustment += int(clarity / 40)
        
        # 파워 (적당한 파워가 고음에 유리)
        if spl > -20:
            score_adjustment += 1
        
        # 최종 음표 계산
        final_idx = max(0, min(len(base_notes) - 1, base_idx + score_adjustment))
        
        return base_notes[final_idx]