"""
SongLab 딥러닝 학습용 데이터 파이프라인
음성 데이터를 수집하고 전처리하여 학습용 데이터셋 생성
"""

import os
import json
import torch
import numpy as np
import soundfile as sf
import parselmouth
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
import logging

logger = logging.getLogger(__name__)

class VocalDataset(Dataset):
    """보컬 분석을 위한 PyTorch Dataset"""
    
    def __init__(self, 
                 audio_files: List[str], 
                 labels: List[Dict], 
                 sample_rate: int = 16000,
                 duration: float = 30.0):
        """
        Args:
            audio_files: 오디오 파일 경로 리스트
            labels: 4축 분석 결과 라벨 리스트
            sample_rate: 샘플링 주파수
            duration: 오디오 길이 (초)
        """
        self.audio_files = audio_files
        self.labels = labels
        self.sample_rate = sample_rate
        self.duration = duration
        self.target_length = int(sample_rate * duration)
        
    def __len__(self):
        return len(self.audio_files)
    
    def __getitem__(self, idx):
        # 오디오 로드
        audio_path = self.audio_files[idx]
        audio, sr = sf.read(audio_path)
        
        # 리샘플링 (필요시)
        if sr != self.sample_rate:
            audio = self._resample(audio, sr, self.sample_rate)
        
        # 길이 조정
        audio = self._adjust_length(audio)
        
        # 특징 추출
        features = self._extract_features(audio)
        
        # 라벨 준비
        label = self.labels[idx]
        target = torch.tensor([
            label.get('brightness', 0.5),
            label.get('thickness', 0.5), 
            label.get('loudness', 0.5),
            label.get('clarity', 0.5)
        ], dtype=torch.float32)
        
        return {
            'features': features,
            'audio': torch.tensor(audio, dtype=torch.float32),
            'target': target,
            'metadata': {
                'file_path': audio_path,
                'original_label': label
            }
        }
    
    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """오디오 리샘플링"""
        # 간단한 리샘플링 (실제로는 librosa.resample 사용하지만 알러지가 있으므로)
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)
    
    def _adjust_length(self, audio: np.ndarray) -> np.ndarray:
        """오디오 길이 조정"""
        if len(audio) > self.target_length:
            # 랜덤 크롭
            start = np.random.randint(0, len(audio) - self.target_length)
            return audio[start:start + self.target_length]
        else:
            # 제로 패딩
            pad_length = self.target_length - len(audio)
            return np.pad(audio, (0, pad_length), mode='constant')
    
    def _extract_features(self, audio: np.ndarray) -> torch.Tensor:
        """음성 특징 추출"""
        try:
            # Parselmouth를 사용한 특징 추출
            sound = parselmouth.Sound(audio, sampling_frequency=self.sample_rate)
            
            # 기본 특징들
            features = {}
            
            # 1. Pitch 관련
            pitch = sound.to_pitch()
            f0_values = pitch.selected_array['frequency']
            f0_values = f0_values[f0_values != 0]  # 유성음만
            
            if len(f0_values) > 0:
                features['f0_mean'] = np.mean(f0_values)
                features['f0_std'] = np.std(f0_values)
                features['f0_min'] = np.min(f0_values)
                features['f0_max'] = np.max(f0_values)
            else:
                features.update({
                    'f0_mean': 0, 'f0_std': 0, 'f0_min': 0, 'f0_max': 0
                })
            
            # 2. 포먼트
            formants = sound.to_formant_burg()
            f1_values = []
            f2_values = []
            
            for i in range(formants.get_number_of_frames()):
                f1 = formants.get_value_at_time(1, formants.get_time_from_frame_number(i + 1))
                f2 = formants.get_value_at_time(2, formants.get_time_from_frame_number(i + 1))
                if not np.isnan(f1):
                    f1_values.append(f1)
                if not np.isnan(f2):
                    f2_values.append(f2)
            
            features['f1_mean'] = np.mean(f1_values) if f1_values else 0
            features['f2_mean'] = np.mean(f2_values) if f2_values else 0
            
            # 3. 에너지 관련
            intensity = sound.to_intensity()
            intensity_values = intensity.values[intensity.values != 0]
            
            if len(intensity_values) > 0:
                features['intensity_mean'] = np.mean(intensity_values)
                features['intensity_std'] = np.std(intensity_values)
            else:
                features['intensity_mean'] = 0
                features['intensity_std'] = 0
            
            # 4. 스펙트럴 특징
            spectrum = sound.to_spectrum()
            freq_bins = spectrum.get_frequency_grid()
            power_spectrum = spectrum.get_power_spectrum_at_time(sound.duration / 2)
            
            # 스펙트럴 중심
            spectral_centroid = np.sum(freq_bins * power_spectrum) / np.sum(power_spectrum)
            features['spectral_centroid'] = spectral_centroid
            
            # 스펙트럴 롤오프
            cumsum = np.cumsum(power_spectrum)
            rolloff_idx = np.where(cumsum >= 0.85 * cumsum[-1])[0][0]
            features['spectral_rolloff'] = freq_bins[rolloff_idx]
            
            # 5. MFCC (간단 버전)
            # 실제로는 더 복잡한 MFCC 계산이 필요하지만 Parselmouth 기능 활용
            features['zcr'] = np.mean(np.abs(np.diff(np.sign(audio))))
            
            # 특징 벡터로 변환
            feature_vector = [
                features.get('f0_mean', 0) / 500.0,  # 정규화
                features.get('f0_std', 0) / 100.0,
                features.get('f1_mean', 0) / 3000.0,
                features.get('f2_mean', 0) / 3000.0,
                features.get('intensity_mean', 0) / 80.0,
                features.get('intensity_std', 0) / 20.0,
                features.get('spectral_centroid', 0) / 8000.0,
                features.get('spectral_rolloff', 0) / 8000.0,
                features.get('zcr', 0)
            ]
            
            return torch.tensor(feature_vector, dtype=torch.float32)
            
        except Exception as e:
            logger.warning(f"특징 추출 실패: {e}")
            # 기본 특징 벡터 반환
            return torch.zeros(9, dtype=torch.float32)


class DataCollector:
    """음성 데이터 수집 및 관리"""
    
    def __init__(self, data_dir: str = "data/collected"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.audio_dir = self.data_dir / "audio"
        self.labels_dir = self.data_dir / "labels"
        
        self.audio_dir.mkdir(exist_ok=True)
        self.labels_dir.mkdir(exist_ok=True)
        
        self.metadata_file = self.data_dir / "metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """메타데이터 로드"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'total_samples': 0,
            'samples': []
        }
    
    def _save_metadata(self):
        """메타데이터 저장"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def add_sample(self, 
                   audio_data: np.ndarray, 
                   sample_rate: int,
                   analysis_result: Dict,
                   user_consent: bool = True) -> str:
        """새 샘플 추가"""
        if not user_consent:
            logger.info("사용자 동의 없음 - 데이터 수집 건너뜀")
            return None
        
        # 고유 ID 생성
        sample_id = f"sample_{self.metadata['total_samples']:06d}"
        
        # 오디오 파일 저장
        audio_path = self.audio_dir / f"{sample_id}.wav"
        sf.write(audio_path, audio_data, sample_rate)
        
        # 라벨 저장
        label_path = self.labels_dir / f"{sample_id}.json"
        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        # 메타데이터 업데이트
        sample_info = {
            'id': sample_id,
            'audio_path': str(audio_path),
            'label_path': str(label_path),
            'sample_rate': sample_rate,
            'duration': len(audio_data) / sample_rate,
            'analysis_result': analysis_result,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        self.metadata['samples'].append(sample_info)
        self.metadata['total_samples'] += 1
        self._save_metadata()
        
        logger.info(f"새 샘플 추가: {sample_id}")
        return sample_id
    
    def get_dataset(self, test_size: float = 0.2) -> Tuple[VocalDataset, VocalDataset]:
        """학습/테스트 데이터셋 생성"""
        if self.metadata['total_samples'] == 0:
            raise ValueError("수집된 데이터가 없습니다")
        
        audio_files = []
        labels = []
        
        for sample in self.metadata['samples']:
            audio_files.append(sample['audio_path'])
            labels.append(sample['analysis_result'])
        
        # 학습/테스트 분할
        train_files, test_files, train_labels, test_labels = train_test_split(
            audio_files, labels, test_size=test_size, random_state=42
        )
        
        train_dataset = VocalDataset(train_files, train_labels)
        test_dataset = VocalDataset(test_files, test_labels)
        
        return train_dataset, test_dataset
    
    def get_statistics(self) -> Dict:
        """데이터셋 통계"""
        if self.metadata['total_samples'] == 0:
            return {"message": "수집된 데이터가 없습니다"}
        
        # 기본 통계
        stats = {
            'total_samples': self.metadata['total_samples'],
            'total_duration': sum(s['duration'] for s in self.metadata['samples']),
        }
        
        # 4축 분석 통계
        for axis in ['brightness', 'thickness', 'loudness', 'clarity']:
            values = [s['analysis_result'].get(axis, 0) for s in self.metadata['samples']]
            stats[f'{axis}_mean'] = np.mean(values)
            stats[f'{axis}_std'] = np.std(values)
        
        return stats


# 사용 예시
if __name__ == "__main__":
    # 데이터 수집기 초기화
    collector = DataCollector()
    
    print("현재 데이터셋 통계:")
    print(json.dumps(collector.get_statistics(), indent=2, ensure_ascii=False))
    
    # 데이터셋 생성 (샘플이 있는 경우)
    if collector.metadata['total_samples'] > 10:
        train_dataset, test_dataset = collector.get_dataset()
        
        train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False)
        
        print(f"학습 데이터: {len(train_dataset)} 샘플")
        print(f"테스트 데이터: {len(test_dataset)} 샘플")
        
        # 첫 번째 배치 확인
        for batch in train_loader:
            print(f"Features shape: {batch['features'].shape}")
            print(f"Audio shape: {batch['audio'].shape}")
            print(f"Target shape: {batch['target'].shape}")
            break