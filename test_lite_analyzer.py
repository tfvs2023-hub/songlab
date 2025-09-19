"""
Lite 엔진으로 오디오 파일 분석 테스트
"""

import sys
import os
import soundfile as sf
from vocal_analyzer_lite import VocalAnalyzerLite

def test_analyze_file(file_path):
    print(f"\n{'='*60}")
    print(f"분석 파일: {file_path}")
    print(f"{'='*60}")
    
    # 분석기 초기화
    analyzer = VocalAnalyzerLite()
    
    # 오디오 파일 읽기
    audio_data, sr = sf.read(file_path)
    
    # 바이트로 변환
    import io
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sr, format='WAV')
    audio_bytes = buffer.getvalue()
    
    # 분석 수행
    result = analyzer.analyze(audio_bytes)
    
    # 결과 출력
    print("\n📊 4축 분석 결과 (Lite Engine):")
    print("-" * 40)
    scores = result['scores']
    print(f"✨ 밝기 (Brightness):  {scores['brightness']:+6.1f} {'🌟' if scores['brightness'] > 0 else '🌙'}")
    print(f"🎯 두께 (Thickness):   {scores['thickness']:+6.1f} {'🔴' if scores['thickness'] > 0 else '⚪'}")
    print(f"🔊 음압 (Loudness):    {scores['loudness']:+6.1f} {'💪' if scores['loudness'] > 0 else '🍃'}")
    print(f"💎 선명도 (Clarity):   {scores['clarity']:+6.1f} {'✅' if scores['clarity'] > 0 else '⚠️'}")
    
    # 신뢰도
    confidence = result['confidence']
    print(f"\n🎯 신뢰도: {confidence:.2f}")
    if confidence > 0.7:
        print("   → 높은 신뢰도 ✅")
    elif confidence > 0.3:
        print("   → 보통 신뢰도 ⚠️")
    else:
        print("   → 낮은 신뢰도 ❌")
    
    # 품질 메타데이터
    print("\n📈 품질 메타데이터:")
    print("-" * 40)
    quality = result['quality']
    print(f"LUFS: {quality['lufs']:.1f} dB")
    print(f"SNR: {quality['snr']:.1f} dB")
    print(f"클리핑: {quality['clipping_percent']:.2f}%")
    print(f"무음: {quality['silence_percent']:.1f}%")
    
    # 품질 평가
    print("\n💡 품질 평가:")
    if quality['snr'] < 15:
        print("⚠️ SNR이 낮음 - 잡음이 많습니다")
    if quality['clipping_percent'] > 3:
        print("⚠️ 클리핑 감지 - 음량이 너무 큽니다")
    if quality['silence_percent'] > 60:
        print("⚠️ 무음 구간이 많음 - 더 크게 녹음하세요")
    if quality['snr'] >= 15 and quality['clipping_percent'] <= 3 and quality['silence_percent'] <= 60:
        print("✅ 녹음 품질 양호")
    
    # 보컬 타입 판정
    print("\n🎤 보컬 타입:")
    type_code = ''
    type_code += 'B' if scores['brightness'] > 0 else 'D'
    type_code += 'T' if scores['thickness'] > 0 else 'L'
    type_code += 'S' if scores['loudness'] > 0 else 'W'
    type_code += 'C' if scores['clarity'] > 0 else 'R'
    print(f"   {type_code} 타입")
    
    # 특징 설명
    characteristics = []
    if abs(scores['brightness']) > 30:
        characteristics.append("밝은 음색" if scores['brightness'] > 0 else "어두운 음색")
    if abs(scores['thickness']) > 30:
        characteristics.append("두꺼운 음색" if scores['thickness'] > 0 else "얇은 음색")
    if abs(scores['loudness']) > 30:
        characteristics.append("강한 음압" if scores['loudness'] > 0 else "부드러운 음압")
    if abs(scores['clarity']) > 30:
        characteristics.append("선명한 발성" if scores['clarity'] > 0 else "부드러운 발성")
    
    if characteristics:
        print(f"   특징: {', '.join(characteristics)}")
    
    return result

if __name__ == "__main__":
    file_path = r"C:\Users\user\Desktop\FULL\female4\long_tones\forte\f4_long_forte_a.wav"
    result = test_analyze_file(file_path)