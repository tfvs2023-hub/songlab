# app.py - 보컬 분석 서버
from flask import Flask, request, jsonify
from flask_cors import CORS
import librosa
import numpy as np
import tempfile
import os
import logging
from werkzeug.utils import secure_filename
from scipy import signal
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)  # CORS 설정으로 프론트엔드에서 접근 가능

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 허용되는 파일 확장자
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'ogg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class VocalAnalyzer:
    def __init__(self):
        # 보컬 특성을 실제 MBTI 타입으로 매핑 (16가지 전체)
        # B/D (Bright/Dark) × T/R (Thick/Rich) × C/H (Clear/Husky) × P/S (Power/Soft)
        self.mbti_types = {
            # Bright (밝은) 계열
            'BTCP': {'name': 'ENFP', 'icon': '🎭', 'description': '밝고 두껍고 선명하고 강력한 보컬 스타일'},
            'BTCS': {'name': 'ESFJ', 'icon': '🤗', 'description': '밝고 두껍고 선명하고 부드러운 보컬 스타일'},
            'BTHP': {'name': 'ESTP', 'icon': '🔥', 'description': '밝고 두껍고 허스키하고 강력한 보컬 스타일'},
            'BTHS': {'name': 'ESFP', 'icon': '🎉', 'description': '밝고 두껍고 허스키하고 부드러운 보컬 스타일'},
            'BRCP': {'name': 'ENTJ', 'icon': '👑', 'description': '밝고 풍부하고 선명하고 강력한 보컬 스타일'},
            'BRCS': {'name': 'ENFJ', 'icon': '✨', 'description': '밝고 풍부하고 선명하고 부드러운 보컬 스타일'},
            'BRHP': {'name': 'ENTP', 'icon': '💡', 'description': '밝고 풍부하고 허스키하고 강력한 보컬 스타일'},
            'BRHS': {'name': 'ESTJ', 'icon': '📣', 'description': '밝고 풍부하고 허스키하고 부드러운 보컬 스타일'},
            
            # Dark (어두운) 계열  
            'DTCP': {'name': 'INTP', 'icon': '🔬', 'description': '어둡고 두껍고 선명하고 강력한 보컬 스타일'},
            'DTCS': {'name': 'ISFJ', 'icon': '🌙', 'description': '어둡고 두껍고 선명하고 부드러운 보컬 스타일'},
            'DTHP': {'name': 'ISTP', 'icon': '🛠️', 'description': '어둡고 두껍고 허스키하고 강력한 보컬 스타일'},
            'DTHS': {'name': 'ISFP', 'icon': '🎨', 'description': '어둡고 두껍고 허스키하고 부드러운 보컬 스타일'},
            'DRCP': {'name': 'INTJ', 'icon': '🎯', 'description': '어둡고 풍부하고 선명하고 강력한 보컬 스타일'},
            'DRCS': {'name': 'INFJ', 'icon': '🌟', 'description': '어둡고 풍부하고 선명하고 부드러운 보컬 스타일'},
            'DRHP': {'name': 'INFP', 'icon': '🌊', 'description': '어둡고 풍부하고 허스키하고 강력한 보컬 스타일'},
            'DRHS': {'name': 'ISTJ', 'icon': '🏛️', 'description': '어둡고 풍부하고 허스키하고 부드러운 보컬 스타일'}
        }

    def extract_audio_features(self, audio_path):
        """음성 파일에서 특징 추출"""
        try:
            # librosa로 음성 로드
            y, sr = librosa.load(audio_path, sr=22050)
            
            # 기본 특징들 추출
            features = {}
            
            # 1. 스펙트럴 센트로이드 (밝기와 관련)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            features['spectral_centroid_mean'] = np.mean(spectral_centroids)
            features['spectral_centroid_std'] = np.std(spectral_centroids)
            
            # 2. 스펙트럴 롤오프 (음색의 두께와 관련)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            features['spectral_rolloff_mean'] = np.mean(spectral_rolloff)
            
            # 3. MFCC (음색 특성)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            for i in range(13):
                features[f'mfcc_{i}_mean'] = np.mean(mfccs[i])
                features[f'mfcc_{i}_std'] = np.std(mfccs[i])
            
            # 4. 제로 크로싱 레이트 (선명도와 관련)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            features['zcr_mean'] = np.mean(zcr)
            features['zcr_std'] = np.std(zcr)
            
            # 5. RMS 에너지 (음압과 관련)
            rms = librosa.feature.rms(y=y)[0]
            features['rms_mean'] = np.mean(rms)
            features['rms_std'] = np.std(rms)
            
            # 6. 피치 분석
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                features['pitch_mean'] = np.mean(pitch_values)
                features['pitch_std'] = np.std(pitch_values)
                features['pitch_range'] = np.max(pitch_values) - np.min(pitch_values)
            else:
                features['pitch_mean'] = 0
                features['pitch_std'] = 0
                features['pitch_range'] = 0
            
            # 7. 하모닉과 퍼커시브 분리
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            features['harmonic_ratio'] = np.mean(np.abs(y_harmonic)) / (np.mean(np.abs(y)) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"특징 추출 오류: {e}")
            return None

    def calculate_vocal_scores(self, features):
        """특징을 바탕으로 보컬 점수 계산"""
        try:
            scores = {}
            
            # 1. 밝기 (Brightness) - 스펙트럴 센트로이드 기반
            brightness_raw = features['spectral_centroid_mean'] / 10000  # 정규화
            brightness_raw = min(brightness_raw, 1.0)  # 최대값 제한
            scores['brightness'] = brightness_raw * 100
            
            # 2. 두께 (Thickness) - 스펙트럴 롤오프와 낮은 주파수 성분
            thickness_raw = 1.0 - (features['spectral_rolloff_mean'] / 20000)
            thickness_raw = max(0, min(thickness_raw, 1.0))
            scores['thickness'] = thickness_raw * 100
            
            # 3. 선명도 (Clarity) vs 허스키함 - ZCR과 하모닉 비율
            clarity_raw = features['zcr_mean'] * 10  # ZCR 기반
            clarity_raw = min(clarity_raw, 1.0)
            # 하모닉 비율도 고려 (높을수록 선명)
            harmonic_clarity = features['harmonic_ratio']
            clarity_raw = (clarity_raw + harmonic_clarity) / 2
            scores['clarity'] = clarity_raw * 100
            
            # 4. 음압 (Power) vs 부드러움 - RMS 에너지와 다이나믹 레인지
            power_raw = features['rms_mean'] * 5  # RMS 기반
            power_raw = min(power_raw, 1.0)
            # RMS 표준편차도 고려 (높을수록 강력함)
            dynamic_power = features['rms_std'] * 10
            power_raw = (power_raw + min(dynamic_power, 1.0)) / 2
            scores['power'] = power_raw * 100
            
            # 점수 정규화 (0-100 범위)
            for key in scores:
                scores[key] = max(0, min(100, scores[key]))
            
            return scores
            
        except Exception as e:
            logger.error(f"점수 계산 오류: {e}")
            return None

    def determine_mbti_type(self, scores):
        """점수를 바탕으로 MBTI 타입 결정"""
        try:
            # 각 차원의 임계값 (50을 기준으로)
            b = 'B' if scores['brightness'] >= 50 else 'D'  # Bright vs Dark
            t = 'T' if scores['thickness'] >= 50 else 'R'   # Thick vs Rich
            c = 'C' if scores['clarity'] >= 50 else 'H'     # Clear vs Husky  
            p = 'P' if scores['power'] >= 50 else 'S'       # Power vs Soft
            
            type_code = b + t + c + p
            
            # 정의되지 않은 타입의 경우 가장 가까운 타입으로 매핑
            if type_code not in self.mbti_types:
                # 기본 타입으로 설정
                type_code = 'BTCP'
            
            mbti_info = self.mbti_types[type_code].copy()
            mbti_info['typeCode'] = type_code
            
            return mbti_info
            
        except Exception as e:
            logger.error(f"MBTI 타입 결정 오류: {e}")
            return self.mbti_types['BTCP'].copy()

    def analyze_audio(self, audio_path):
        """전체 음성 분석 프로세스"""
        try:
            logger.info(f"음성 분석 시작: {audio_path}")
            
            # 1. 특징 추출
            features = self.extract_audio_features(audio_path)
            if features is None:
                return None
            
            # 2. 점수 계산
            scores = self.calculate_vocal_scores(features)
            if scores is None:
                return None
            
            # 3. MBTI 타입 결정
            mbti = self.determine_mbti_type(scores)
            
            result = {
                'scores': scores,
                'mbti': mbti,
                'features': features  # 디버깅용
            }
            
            logger.info(f"분석 완료: {mbti['typeCode']}")
            return result
            
        except Exception as e:
            logger.error(f"음성 분석 오류: {e}")
            return None

# 전역 분석기 인스턴스
analyzer = VocalAnalyzer()

@app.route('/analyze', methods=['POST'])
def analyze_voice():
    try:
        logger.info("음성 분석 요청 받음")
        
        # 파일 확인
        if 'file' not in request.files:
            logger.error("파일이 없음")
            return jsonify({'success': False, 'message': '파일이 없습니다'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("파일명이 없음")
            return jsonify({'success': False, 'message': '파일이 선택되지 않았습니다'}), 400
        
        if not allowed_file(file.filename):
            logger.error(f"지원하지 않는 파일 형식: {file.filename}")
            return jsonify({'success': False, 'message': '지원하지 않는 파일 형식입니다'}), 400
        
        # 임시 파일로 저장
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        
        file.save(temp_path)
        logger.info(f"파일 저장됨: {temp_path}")
        
        # 음성 분석 수행
        result = analyzer.analyze_audio(temp_path)
        
        # 임시 파일 삭제
        try:
            os.remove(temp_path)
            os.rmdir(temp_dir)
        except:
            pass
        
        if result is None:
            logger.error("분석 실패")
            return jsonify({'success': False, 'message': '음성 분석에 실패했습니다'}), 500
        
        # 성공 응답
        response = {
            'success': True,
            'status': 'success',
            'mbti': {
                'typeCode': result['mbti']['typeCode'],
                'typeName': result['mbti']['name'],
                'typeIcon': result['mbti']['icon'],
                'description': result['mbti']['description'],
                'scores': result['scores']
            }
        }
        
        logger.info("분석 결과 반환")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"서버 오류: {e}")
        return jsonify({'success': False, 'message': f'서버 오류: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({'status': 'healthy', 'message': '보컬 분석 서버가 정상 작동 중입니다'})

@app.route('/', methods=['GET'])
def index():
    """기본 페이지"""
    return jsonify({
        'message': '보컬 분석 API 서버',
        'version': '1.0.0',
        'endpoints': {
            '/analyze': 'POST - 음성 파일 분석',
            '/health': 'GET - 서버 상태 확인'
        }
    })

if __name__ == '__main__':
    logger.info("보컬 분석 서버 시작")
    app.run(host='127.0.0.1', port=8001, debug=True)  # 포트를 5000으로 변경