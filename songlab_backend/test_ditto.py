"""
딧토2.m4a 파일 테스트
"""

from voice_analyzer import VoiceAnalyzer
import soundfile as sf
import io
import subprocess
import tempfile
import os

def convert_m4a_to_wav(m4a_path):
    """M4A를 WAV로 변환 (ffmpeg 사용)"""
    try:
        # 임시 WAV 파일 생성
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        # ffmpeg로 변환
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

def test_ditto():
    """딧토2.m4a 분석"""
    
    print("=" * 60)
    print("🎤 딧토2.m4a 고급 4축 보컬 분석")
    print("=" * 60)
    
    # M4A 파일 경로
    m4a_file = r"C:\Users\user\Documents\카카오톡 받은 파일\딧토2.m4a"
    
    # 분석기 초기화
    analyzer = VoiceAnalyzer()
    print("✅ 분석기 초기화 완료")
    
    try:
        # M4A를 WAV로 변환
        print("🔄 M4A → WAV 변환 중...")
        wav_path = convert_m4a_to_wav(m4a_file)
        
        if not wav_path:
            # soundfile로 직접 시도
            print("📁 soundfile로 직접 로드 시도...")
            audio_data, sr = sf.read(m4a_file)
        else:
            # 변환된 WAV 로드
            audio_data, sr = sf.read(wav_path)
            # 임시 파일 삭제
            os.unlink(wav_path)
        
        print(f"🎵 오디오 로드 완료: {len(audio_data)/sr:.1f}초, {sr}Hz")
        
        # 바이트로 변환
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sr, format='wav')
        audio_bytes = audio_buffer.getvalue()
        
        # 고급 분석 수행
        print("\n🔍 4축 분석 수행중...")
        results = analyzer.get_advanced_results(audio_bytes)
        
        # 결과 출력
        print("\n" + "="*60)
        print("📈 분석 결과")
        print("="*60)
        
        print("\n[4축 분석]")
        print(f"🌟 밝기 (Brightness):     {results['brightness']:+6.1f}")
        print(f"🎭 두께 (Thickness):      {results['thickness']:+6.1f}")
        print(f"🎯 성대내전 (Adduction):   {results['adduction']:+6.1f}")
        print(f"📢 음압 (SPL):           {results['spl']:+6.1f}")
        
        print("\n[추론 결과]")
        print(f"👤 성별:                 {results['gender']}")
        print(f"🎵 잠재적 고음력:         {results['potential_high_note']}")
        
        # 이전 파일들과 비교
        print("\n" + "="*60)
        print("📊 비교 분석")
        print("="*60)
        
        print("\n파일명     | 밝기   | 두께   | 성대내전 | 음압   | 성별 | 고음력")
        print("-" * 70)
        print("상일2      | -25.2  | +100.0 |  +13.0   | +82.8  | 여성 | D#5")
        print("일반인추사 | +100.0 | +100.0 | -100.0   | +70.6  | 여성 | E5")
        print(f"딧토2      | {results['brightness']:+6.1f} | {results['thickness']:+6.1f} | {results['adduction']:+7.1f} | {results['spl']:+6.1f} | {results['gender'][:2]} | {results['potential_high_note']}")
        
        # 특성 분석
        print("\n" + "="*60)
        print("💡 딧토2 특성 분석")
        print("="*60)
        
        brightness = results['brightness']
        thickness = results['thickness']
        adduction = results['adduction']
        spl = results['spl']
        
        print(f"\n🎯 종합 평가:")
        
        # 밝기
        if brightness > 30:
            print(f"   밝기: 매우 밝은 톤 ({brightness:+.1f})")
        elif brightness > 0:
            print(f"   밝기: 밝은 톤 ({brightness:+.1f})")
        elif brightness > -30:
            print(f"   밝기: 중간 톤 ({brightness:+.1f})")
        else:
            print(f"   밝기: 어두운 톤 ({brightness:+.1f})")
        
        # 두께
        if thickness > 30:
            print(f"   두께: 매우 두꺼운 음색 ({thickness:+.1f})")
        elif thickness > 0:
            print(f"   두께: 두꺼운 음색 ({thickness:+.1f})")
        elif thickness > -30:
            print(f"   두께: 중간 두께 ({thickness:+.1f})")
        else:
            print(f"   두께: 얇은 음색 ({thickness:+.1f})")
        
        # 성대내전
        if adduction > 50:
            print(f"   성대내전: 매우 우수 ({adduction:+.1f}) - 프로페셔널")
        elif adduction > 20:
            print(f"   성대내전: 양호 ({adduction:+.1f}) - 안정적")
        elif adduction > -20:
            print(f"   성대내전: 보통 ({adduction:+.1f}) - 평균적")
        else:
            print(f"   성대내전: 개선 필요 ({adduction:+.1f})")
        
        # 음압
        if spl > 50:
            print(f"   음압: 매우 강함 ({spl:+.1f})")
        elif spl > 20:
            print(f"   음압: 강함 ({spl:+.1f})")
        else:
            print(f"   음압: 보통 ({spl:+.1f})")
        
        print(f"\n   성별: {results['gender']}")
        print(f"   잠재적 고음력: {results['potential_high_note']}")
        
        # 특별한 특징
        print(f"\n📍 특별한 특징:")
        
        # 가장 높은 점수
        scores = {
            '밝기': brightness,
            '두께': thickness,
            '성대내전': adduction,
            '음압': spl
        }
        
        best_feature = max(scores, key=scores.get)
        print(f"   강점: {best_feature} ({scores[best_feature]:+.1f})")
        
        worst_feature = min(scores, key=scores.get)
        if scores[worst_feature] < 0:
            print(f"   개선점: {worst_feature} ({scores[worst_feature]:+.1f})")
        
        print("\n✅ 딧토2.m4a 분석 완료!")
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_ditto()