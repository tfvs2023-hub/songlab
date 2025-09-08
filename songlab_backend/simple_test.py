"""
간단한 로컬 테스트 스크립트
강윤호 음성 파일로 CREPE 분석 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_basic_analysis():
    """기본 분석 기능 테스트"""
    print("🎵 SongLab 로컬 테스트 시작...")
    
    try:
        # 1. VocalAnalyzer 임포트 테스트
        print("📦 VocalAnalyzer 로딩 중...")
        from vocal_analyzer import VocalAnalyzer
        analyzer = VocalAnalyzer()
        print("✅ VocalAnalyzer 로딩 성공")
        
        # 2. MBTI Engine 테스트
        print("🧠 MBTI Engine 로딩 중...")
        from mbti_engine import MBTIVocalEngine
        mbti_engine = MBTIVocalEngine()
        print("✅ MBTI Engine 로딩 성공")
        
        # 3. 샘플 점수로 MBTI 테스트
        print("🎯 MBTI 타입 분석 테스트...")
        sample_scores = {
            'brightness': -45,  # 깊은 톤
            'thickness': 67,    # 두꺼운 음색
            'clarity': 23,      # 약간 선명
            'power': 78         # 강한 발성
        }
        
        mbti_result = mbti_engine.analyze_mbti_type(sample_scores, 'male')
        
        print(f"\n🎤 분석 결과:")
        print(f"   타입: {mbti_result['name']} ({mbti_result['type_code']})")
        print(f"   설명: {mbti_result['desc']}")
        print(f"   장점: {mbti_result['pros'][:2]}")
        print(f"   단점: {mbti_result['cons'][:2]}")
        print(f"   추천곡: {mbti_result['songs'][:2]}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 패키지 오류: {e}")
        print("다음 명령어로 패키지 설치:")
        print("pip install librosa soundfile numpy scipy torch")
        return False
    except Exception as e:
        print(f"❌ 분석 오류: {e}")
        return False

def test_audio_file():
    """실제 음성 파일 분석 테스트"""
    audio_file = r"C:\Users\user\Desktop\강윤호 이승철 0522.m4a"
    
    if not os.path.exists(audio_file):
        print(f"❌ 음성 파일을 찾을 수 없습니다: {audio_file}")
        return False
    
    try:
        print(f"🎵 음성 파일 분석 시작: {os.path.basename(audio_file)}")
        
        from vocal_analyzer import VocalAnalyzer
        analyzer = VocalAnalyzer()
        
        # 실제 분석 실행
        result = analyzer.analyze_audio(audio_file)
        
        print(f"\n🎉 강윤호님 음성 분석 완료!")
        print(f"   타입: {result['mbti']['typeName']}")
        print(f"   현재 최고음: {result['mbti']['currentNote']}")
        print(f"   잠재 최고음: {result['mbti']['potentialNote']}")
        
        # MBTI 점수 출력
        scores = result['mbti']['scores']
        print(f"\n📊 MBTI 점수:")
        print(f"   밝기: {scores['brightness']:+d} ({'밝음' if scores['brightness'] > 0 else '깊음'})")
        print(f"   두께: {scores['thickness']:+d} ({'두꺼움' if scores['thickness'] > 0 else '얇음'})")
        print(f"   선명도: {scores['clarity']:+d} ({'선명' if scores['clarity'] > 0 else '개성적'})")
        print(f"   파워: {scores['power']:+d} ({'강함' if scores['power'] > 0 else '부드러움'})")
        
        return True
        
    except Exception as e:
        print(f"❌ 음성 분석 실패: {e}")
        print("librosa, crepe 패키지 설치 필요할 수 있습니다.")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🎤 SongLab CREPE 분석 엔진 로컬 테스트")
    print("=" * 50)
    
    # 1. 기본 기능 테스트
    if test_basic_analysis():
        print("\n" + "=" * 30)
        
        # 2. 실제 음성 파일 테스트
        test_audio_file()
    
    print("\n🏁 테스트 완료!")