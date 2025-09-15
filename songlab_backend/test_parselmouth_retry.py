"""
Parselmouth 재시도 - 더 관대한 설정으로 HNR, Jitter, Shimmer 측정
"""

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call
import subprocess
import tempfile
import os

def convert_m4a_to_wav(m4a_path):
    """M4A를 WAV로 변환"""
    try:
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        cmd = [
            'ffmpeg', '-i', m4a_path,
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            temp_wav_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return None
            
        return temp_wav_path
        
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

def analyze_parselmouth_gentle(audio, sr):
    """관대한 설정으로 Parselmouth 분석"""
    
    print(f"🎵 Parselmouth 분석 시작 (SR: {sr}Hz, 길이: {len(audio)/sr:.1f}초)")
    
    try:
        # 원본 샘플링 레이트 유지
        sound = parselmouth.Sound(audio, sampling_frequency=sr)
        
        results = {}
        
        # 1. HNR (Harmonic-to-Noise Ratio) - 매우 관대한 설정
        print("\n🎯 HNR 분석...")
        try:
            harmonicity = sound.to_harmonicity(
                time_step=0.01,           # 10ms 간격
                minimum_pitch=50,         # 매우 낮은 최소 피치 (50Hz)
                silence_threshold=0.03,   # 낮은 침묵 임계값 (3%)
                periods_per_window=1.0    # 짧은 윈도우
            )
            
            hnr_values = harmonicity.values.flatten()
            valid_hnr = hnr_values[~np.isnan(hnr_values)]
            
            if len(valid_hnr) > 0:
                hnr_mean = np.mean(valid_hnr)
                hnr_std = np.std(valid_hnr)
                hnr_median = np.median(valid_hnr)
                
                print(f"   ✅ HNR 성공: 평균={hnr_mean:.2f}dB, 중앙값={hnr_median:.2f}dB, 표준편차={hnr_std:.2f}dB")
                print(f"   유효 샘플: {len(valid_hnr)}/{len(hnr_values)}")
                
                results['hnr'] = {
                    'mean': hnr_mean,
                    'median': hnr_median,
                    'std': hnr_std,
                    'valid_samples': len(valid_hnr),
                    'total_samples': len(hnr_values)
                }
            else:
                print("   ❌ HNR 실패: 유효한 값 없음")
                results['hnr'] = None
                
        except Exception as e:
            print(f"   ❌ HNR 오류: {e}")
            results['hnr'] = None
        
        # 2. 피치 분석 및 Jitter
        print("\n🎯 피치 및 Jitter 분석...")
        try:
            pitch = sound.to_pitch(
                time_step=0.01,           # 10ms 간격
                pitch_floor=50.0,         # 50Hz
                pitch_ceiling=800.0       # 800Hz (더 높은 상한)
            )
            
            # 피치 통계
            pitch_values = pitch.selected_array['frequency']
            valid_pitch = pitch_values[~np.isnan(pitch_values)]
            
            if len(valid_pitch) > 10:
                pitch_mean = np.mean(valid_pitch)
                pitch_std = np.std(valid_pitch)
                
                print(f"   ✅ 피치 성공: 평균={pitch_mean:.1f}Hz, 표준편차={pitch_std:.2f}Hz")
                print(f"   유효 샘플: {len(valid_pitch)}/{len(pitch_values)}")
                
                # Jitter 계산
                try:
                    jitter_local = call(pitch, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
                    jitter_ppq5 = call(pitch, "Get jitter (ppq5)", 0, 0, 0.0001, 0.02, 1.3)
                    
                    print(f"   ✅ Jitter 성공: Local={jitter_local:.6f}, PPQ5={jitter_ppq5:.6f}")
                    
                    results['pitch'] = {
                        'mean': pitch_mean,
                        'std': pitch_std,
                        'valid_samples': len(valid_pitch)
                    }
                    results['jitter'] = {
                        'local': jitter_local,
                        'ppq5': jitter_ppq5
                    }
                    
                except Exception as e:
                    print(f"   ❌ Jitter 계산 오류: {e}")
                    results['pitch'] = {
                        'mean': pitch_mean,
                        'std': pitch_std,
                        'valid_samples': len(valid_pitch)
                    }
                    results['jitter'] = None
            else:
                print("   ❌ 피치 실패: 유효한 값 부족")
                results['pitch'] = None
                results['jitter'] = None
                
        except Exception as e:
            print(f"   ❌ 피치 분석 오류: {e}")
            results['pitch'] = None
            results['jitter'] = None
        
        # 3. Shimmer
        print("\n🎯 Shimmer 분석...")
        try:
            shimmer_local = call(sound, "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
            shimmer_apq3 = call(sound, "Get shimmer (apq3)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
            
            print(f"   ✅ Shimmer 성공: Local={shimmer_local:.6f}, APQ3={shimmer_apq3:.6f}")
            
            results['shimmer'] = {
                'local': shimmer_local,
                'apq3': shimmer_apq3
            }
            
        except Exception as e:
            print(f"   ❌ Shimmer 오류: {e}")
            results['shimmer'] = None
        
        # 4. 성대내전 점수 계산 (개선된 버전)
        print("\n🎯 성대내전 점수 계산...")
        
        adduction_components = []
        
        # HNR 점수 (가장 중요)
        if results['hnr']:
            hnr_mean = results['hnr']['mean']
            # MR 제거 보컬용 HNR 기준 (더 관대하게)
            hnr_score = np.clip((hnr_mean + 5) * 4, -40, 40)  # -5dB를 중심으로
            adduction_components.append(('HNR', hnr_score, 0.5))
            print(f"   HNR 점수: {hnr_score:.1f} (가중치: 50%)")
        
        # Jitter 점수
        if results['jitter']:
            jitter_local = results['jitter']['local']
            jitter_score = np.clip(30 - jitter_local * 5000, -30, 30)
            adduction_components.append(('Jitter', jitter_score, 0.25))
            print(f"   Jitter 점수: {jitter_score:.1f} (가중치: 25%)")
        
        # Shimmer 점수
        if results['shimmer']:
            shimmer_local = results['shimmer']['local']
            shimmer_score = np.clip(30 - shimmer_local * 500, -30, 30)
            adduction_components.append(('Shimmer', shimmer_score, 0.25))
            print(f"   Shimmer 점수: {shimmer_score:.1f} (가중치: 25%)")
        
        # 최종 성대내전 점수
        if adduction_components:
            total_weight = sum(weight for _, _, weight in adduction_components)
            weighted_score = sum(score * weight for _, score, weight in adduction_components)
            final_score = weighted_score / total_weight if total_weight > 0 else 0
            
            print(f"   최종 점수: {final_score:.1f} (-50~50)")
            
            # 음성 타입 판정
            if final_score > 20:
                voice_type = "excellent_chest_voice"
                evaluation = "매우 좋음 (완벽한 진성)"
            elif final_score > 10:
                voice_type = "good_chest_voice" 
                evaluation = "좋음 (안정적 진성)"
            elif final_score > 0:
                voice_type = "average_voice"
                evaluation = "보통 (평균적)"
            elif final_score > -15:
                voice_type = "breathy_voice"
                evaluation = "나쁨 (허스키함)"
            else:
                voice_type = "very_breathy"
                evaluation = "매우 나쁨 (심각한 허스키함)"
            
            results['final_adduction'] = {
                'score': final_score,
                'voice_type': voice_type,
                'evaluation': evaluation,
                'components': adduction_components
            }
        else:
            print("   ❌ 성대내전 점수 계산 실패: 유효한 지표 없음")
            results['final_adduction'] = None
        
        return results
        
    except Exception as e:
        print(f"❌ Parselmouth 분석 전체 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_parselmouth_retry(audio_file):
    """Parselmouth 재시도 테스트"""
    
    print("=" * 70)
    print("🔬 Parselmouth 재시도 - 관대한 설정")
    print("=" * 70)
    
    try:
        # 오디오 로드 (M4A 지원)
        if audio_file.endswith('.m4a'):
            print("🔄 M4A → WAV 변환 중...")
            wav_path = convert_m4a_to_wav(audio_file)
            
            if not wav_path:
                print("📁 soundfile로 직접 로드...")
                audio_data, sr = sf.read(audio_file)
            else:
                audio_data, sr = sf.read(wav_path)
                os.unlink(wav_path)
        else:
            audio_data, sr = sf.read(audio_file)
        
        print(f"🎵 파일: {audio_file.split('\\')[-1]}")
        print(f"   길이: {len(audio_data)/sr:.1f}초, 샘플링: {sr}Hz")
        
        # 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 처음 30초만 분석
        max_samples = 30 * sr
        if len(audio_data) > max_samples:
            audio_data = audio_data[:max_samples]
            print("   (처음 30초만 분석)")
        
        # Parselmouth 분석
        results = analyze_parselmouth_gentle(audio_data, sr)
        
        if results and results.get('final_adduction'):
            final = results['final_adduction']
            
            print("\n" + "=" * 70)
            print("📊 최종 결과")
            print("=" * 70)
            print(f"\n🎯 성대내전 분석 결과:")
            print(f"   점수: {final['score']:.1f} (-50~50)")
            print(f"   음성 타입: {final['voice_type']}")
            print(f"   평가: {final['evaluation']}")
            
            print(f"\n📈 구성 요소별 기여도:")
            for name, score, weight in final['components']:
                print(f"   {name}: {score:.1f}점 (가중치 {weight:.0%})")
        else:
            print("\n❌ Parselmouth 분석 실패")
            
        return results
        
    except Exception as e:
        print(f"❌ 테스트 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 3개 파일로 테스트
    files = [
        r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav",  # 진성
        r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a",      # 진성(허스키)
        r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav"                    # 가성
    ]
    
    all_results = []
    for audio_file in files:
        print(f"\n{'='*10} {audio_file.split('\\')[-1]} {'='*10}")
        result = test_parselmouth_retry(audio_file)
        if result and result.get('final_adduction'):
            all_results.append({
                'file': audio_file.split('\\')[-1],
                'score': result['final_adduction']['score'],
                'voice_type': result['final_adduction']['voice_type'],
                'evaluation': result['final_adduction']['evaluation']
            })
        print("\n")
    
    # 최종 비교
    if all_results:
        print("=" * 70)
        print("🏆 Parselmouth 최종 비교")
        print("=" * 70)
        
        print(f"\n{'파일':<30} | {'점수':<6} | {'음성타입':<20} | 평가")
        print("-" * 85)
        
        for r in all_results:
            print(f"{r['file']:<30} | {r['score']:<6.1f} | {r['voice_type']:<20} | {r['evaluation']}")
        
        print(f"\n💡 해석:")
        print(f"   +20 이상: 완벽한 진성")
        print(f"   +10~20: 좋은 진성") 
        print(f"   0~10: 평균적")
        print(f"   -15~0: 허스키함")
        print(f"   -15 이하: 심각한 허스키함/가성")