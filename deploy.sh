#!/bin/bash
# 배포 자동화 스크립트

echo "🚀 SongLab 배포 시작..."

# 1. 프론트엔드 빌드
echo "📦 프론트엔드 빌드 중..."
cd /home/ubuntu/songlab
npm install
npm run build

# 2. 빌드 파일 이동
echo "📁 파일 복사 중..."
sudo rm -rf /var/www/songlab/dist
sudo cp -r dist /var/www/songlab/

# 3. 백엔드 의존성 설치
echo "🐍 백엔드 설정 중..."
cd /home/ubuntu/songlab_advanced
pip install -r requirements.txt

# 4. 서비스 재시작
echo "🔄 서비스 재시작 중..."
sudo systemctl restart songlab
sudo systemctl restart nginx

# 5. 상태 확인
echo "✅ 배포 완료!"
sudo systemctl status songlab --no-pager
sudo systemctl status nginx --no-pager

echo "🌐 https://yourdomain.com 에서 확인하세요!"