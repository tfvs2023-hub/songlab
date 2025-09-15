#!/bin/bash

# SongLab 프로덕션 배포 스크립트

set -e

DOMAIN="${1:-your-domain.com}"
EMAIL="${2:-your-email@example.com}"
PROJECT_PATH="/var/www/songlab"
BACKEND_PATH="/opt/songlab-backend"

echo "=== SongLab 프로덕션 배포 시작 ==="
echo "도메인: $DOMAIN"
echo "이메일: $EMAIL"

# 1. 시스템 업데이트
echo "📦 시스템 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 2. 필요한 패키지 설치
echo "📦 필요한 패키지 설치 중..."
sudo apt install -y nginx python3 python3-pip python3-venv nodejs npm git certbot python3-certbot-nginx

# 3. Node.js 최신 버전 설치
echo "📦 Node.js 설정 중..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 4. 프로젝트 디렉토리 생성
echo "📁 프로젝트 디렉토리 생성 중..."
sudo mkdir -p $PROJECT_PATH
sudo mkdir -p $BACKEND_PATH
sudo chown -R $USER:$USER $PROJECT_PATH
sudo chown -R $USER:$USER $BACKEND_PATH

# 5. 백엔드 설정
echo "🐍 백엔드 설정 중..."
cd $BACKEND_PATH

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 백엔드 의존성 설치
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
librosa==0.10.1
numpy==1.24.3
scipy==1.11.4
soundfile==0.12.1
parselmouth==0.4.3
python-dotenv==1.0.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
alembic==1.13.1
redis==5.0.1
celery==5.3.4
google-api-python-client==2.108.0
requests==2.31.0
Pillow==10.1.0
onnxruntime==1.16.3
torch==2.1.1
torchvision==0.16.1
torchaudio==2.1.1
transformers==4.35.2
EOF

pip install -r requirements.txt

# 6. 프론트엔드 빌드
echo "⚛️  프론트엔드 빌드 중..."
cd $PROJECT_PATH

# 프로덕션 환경변수 설정
cat > .env.production << EOF
VITE_API_URL=https://$DOMAIN/api
NODE_ENV=production
EOF

# 의존성 설치 및 빌드
npm install
npm run build

# 7. Nginx 설정
echo "🌐 Nginx 설정 중..."
sudo cp nginx.conf /etc/nginx/sites-available/songlab

# 도메인 설정 업데이트
sudo sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/songlab

# 심볼릭 링크 생성
sudo ln -sf /etc/nginx/sites-available/songlab /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
sudo nginx -t

# 8. 시스템 서비스 생성
echo "🔧 시스템 서비스 생성 중..."

# 백엔드 서비스
sudo tee /etc/systemd/system/songlab-backend.service > /dev/null << EOF
[Unit]
Description=SongLab Backend API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_PATH
Environment=PATH=$BACKEND_PATH/venv/bin
ExecStart=$BACKEND_PATH/venv/bin/uvicorn main_v2:app --host 127.0.0.1 --port 8002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable songlab-backend
sudo systemctl start songlab-backend

# 9. 방화벽 설정
echo "🔥 방화벽 설정 중..."
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw --force enable

# 10. SSL 인증서 설정
echo "🔒 SSL 인증서 설정 중..."
sudo systemctl start nginx
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email --non-interactive

# 11. 자동 갱신 설정
echo "🔄 자동 갱신 설정 중..."
sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

# 12. 서비스 재시작
echo "🔄 서비스 재시작 중..."
sudo systemctl restart nginx
sudo systemctl restart songlab-backend

# 13. 상태 확인
echo "✅ 배포 상태 확인 중..."
echo "Nginx 상태:"
sudo systemctl status nginx --no-pager -l

echo "백엔드 상태:"
sudo systemctl status songlab-backend --no-pager -l

echo "SSL 인증서 상태:"
sudo certbot certificates

# 14. 배포 완료
echo ""
echo "🎉 SongLab 배포가 완료되었습니다!"
echo ""
echo "📍 URL: https://$DOMAIN"
echo "📍 API: https://$DOMAIN/api"
echo ""
echo "🔧 관리 명령어:"
echo "  sudo systemctl status songlab-backend  # 백엔드 상태 확인"
echo "  sudo systemctl restart songlab-backend # 백엔드 재시작"
echo "  sudo systemctl status nginx            # Nginx 상태 확인"
echo "  sudo nginx -t                          # Nginx 설정 테스트"
echo "  sudo certbot renew                     # SSL 인증서 갱신"
echo ""
echo "📊 로그 확인:"
echo "  sudo journalctl -u songlab-backend -f  # 백엔드 로그"
echo "  sudo tail -f /var/log/nginx/songlab_access.log  # 접속 로그"
echo "  sudo tail -f /var/log/nginx/songlab_error.log   # 에러 로그"