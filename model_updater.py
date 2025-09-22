"""
딥러닝 모델 업데이트 시스템
오프라인 학습 → 온라인 배포
"""

import hashlib
import json
import os
from datetime import datetime

import requests


class ModelUpdater:
    def __init__(self, model_dir="models/"):
        self.model_dir = model_dir
        self.current_version = self.load_version_info()

    def load_version_info(self):
        """현재 모델 버전 정보 로드"""
        version_file = os.path.join(self.model_dir, "version.json")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return json.load(f)
        return {"version": "1.0.0", "date": None, "hash": None}

    def download_new_model(self, model_url):
        """새 모델 다운로드"""
        response = requests.get(model_url, stream=True)
        temp_path = os.path.join(self.model_dir, "temp_model.onnx")

        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return temp_path

    def validate_model(self, model_path):
        """모델 무결성 검증"""
        import onnxruntime as ort

        try:
            # ONNX 모델 로드 테스트
            session = ort.InferenceSession(model_path)

            # 간단한 추론 테스트
            test_input = np.random.randn(1, 16000).astype(np.float32)
            outputs = session.run(None, {"input": test_input})

            return True
        except Exception as e:
            print(f"Model validation failed: {e}")
            return False

    def update_model(self, new_model_path, version="2.0.0"):
        """모델 업데이트 (무중단)"""
        if not self.validate_model(new_model_path):
            raise ValueError("Invalid model file")

        # 백업
        current_model = os.path.join(self.model_dir, "vocal_model.onnx")
        backup_path = os.path.join(
            self.model_dir, f"backup_v{self.current_version['version']}.onnx"
        )

        if os.path.exists(current_model):
            os.rename(current_model, backup_path)

        # 새 모델 적용
        os.rename(new_model_path, current_model)

        # 버전 정보 업데이트
        with open(os.path.join(self.model_dir, "version.json"), "w") as f:
            json.dump(
                {
                    "version": version,
                    "date": datetime.now().isoformat(),
                    "hash": self.get_file_hash(current_model),
                },
                f,
            )

        print(f"Model updated to v{version}")
        return True

    def rollback(self):
        """이전 버전으로 롤백"""
        backup_path = os.path.join(
            self.model_dir, f"backup_v{self.current_version['version']}.onnx"
        )

        if os.path.exists(backup_path):
            current_model = os.path.join(self.model_dir, "vocal_model.onnx")
            os.rename(backup_path, current_model)
            print("Rollback successful")
            return True
        return False

    def get_file_hash(self, filepath):
        """파일 해시 계산"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


# 사용 예시
if __name__ == "__main__":
    updater = ModelUpdater()

    # 새 모델 다운로드 및 업데이트
    # new_model = updater.download_new_model("https://your-storage/vocal_model_v2.onnx")
    # updater.update_model(new_model, version="2.0.0")

    print("Model updater ready")
