#!/bin/bash

# SongLab NCP(네이버 클라우드 플랫폼) 전용 배포 스크립트

set -e

DOMAIN="${1:-your-domain.com}"
EMAIL="${2:-your-email@example.com}"
PROJECT_PATH="/var/www/songlab"
BACKEND_PATH="/opt/songlab-backend"

echo "🚀 SongLab NCP 배포 시작"
echo "📍 도메인: $DOMAIN"
echo "📧 이메일: $EMAIL"
echo "💰 예상 비용: 월 29,260원 (서버+IP+트래픽)"

# 1. 시스템 정보 확인
echo "📊 시스템 정보 확인 중..."
echo "OS: $(lsb_release -d | cut -f2)"
echo "CPU: $(nproc) cores"
echo "Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $2}')"

# 2. NCP 최적화 설정
echo "⚙️ NCP 최적화 설정 중..."

# 시간대 설정 (한국 시간)
timedatectl set-timezone Asia/Seoul

# 시스템 업데이트
apt update && apt upgrade -y

# 한국어 locale 설정
locale-gen ko_KR.UTF-8
update-locale LANG=ko_KR.UTF-8

# 3. 필요한 패키지 설치
echo "📦 패키지 설치 중..."
apt install -y nginx python3 python3-pip python3-venv nodejs npm git curl wget unzip
apt install -y htop iotop nethogs tree fail2ban ufw
apt install -y certbot python3-certbot-nginx

# Node.js 18.x 설치
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# 4. 보안 설정
echo "🔒 보안 설정 중..."

# UFW 방화벽 설정
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'
ufw deny 8002  # API 포트는 외부 접근 차단

# Fail2ban 설정 (SSH 무차별 대입 공격 방지)
systemctl enable fail2ban
systemctl start fail2ban

# 5. 프로젝트 디렉토리 생성
echo "📁 프로젝트 디렉토리 생성 중..."
mkdir -p $PROJECT_PATH
mkdir -p $BACKEND_PATH
mkdir -p /backup
mkdir -p /var/log/songlab

chown -R $USER:$USER $PROJECT_PATH
chown -R $USER:$USER $BACKEND_PATH

# 6. 백엔드 설정
echo "🐍 백엔드 설정 중..."
cd $BACKEND_PATH

# 백엔드 파일 복사 (미리 업로드된 파일 가정)
if [ -d "/tmp/songlab_advanced" ]; then
    cp -r /tmp/songlab_advanced/* .
else
    echo "❌ 백엔드 파일이 /tmp/songlab_advanced에 없습니다."
    echo "먼저 파일을 업로드해주세요: scp -r songlab_advanced root@server:/tmp/"
    exit 1
fi

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치 (NCP 최적화)
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
numpy==1.24.3
scipy==1.11.4
soundfile==0.12.1
parselmouth==0.4.3
python-dotenv==1.0.0
google-api-python-client==2.108.0
requests==2.31.0
onnxruntime==1.16.3
Pillow==10.1.0
psutil==5.9.6
EOF

pip install --upgrade pip
pip install -r requirements.txt

# 7. 프론트엔드 빌드
echo "⚛️ 프론트엔드 빌드 중..."
cd $PROJECT_PATH

# 프론트엔드 파일 복사
if [ -d "/tmp/songlab" ]; then
    cp -r /tmp/songlab/* .
else
    echo "❌ 프론트엔드 파일이 /tmp/songlab에 없습니다."
    exit 1
fi

# 프로덕션 환경변수 설정
cat > .env.production << EOF
VITE_API_URL=https://$DOMAIN/api
NODE_ENV=production
EOF

# NPM 빌드 (메모리 최적화)
export NODE_OPTIONS="--max-old-space-size=1024"
npm install
npm run build

# 8. Nginx 설정 (NCP 최적화)
echo "🌐 Nginx 설정 중..."

# NCP 최적화된 Nginx 설정
cat > /etc/nginx/sites-available/songlab << EOF
# NCP 최적화 설정
server_tokens off;
client_max_body_size 50M;

# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/s;

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    
    # SSL 설정 (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 로그 설정
    access_log /var/log/songlab/access.log;
    error_log /var/log/songlab/error.log;
    
    # Gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # 정적 파일 서빙
    location / {
        root $PROJECT_PATH/dist;
        try_files \$uri \$uri/ /index.html;
        
        # 캐시 설정
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }
    }
    
    # API 프록시 (Rate limiting 적용)
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
    
    # 로그인 API (더 엄격한 Rate limiting)
    location /api/login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://127.0.0.1:8002;
    }
}
EOF

# Nginx 설정 활성화
ln -sf /etc/nginx/sites-available/songlab /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
nginx -t

# 9. 시스템 서비스 생성
echo "🔧 시스템 서비스 생성 중..."

# 백엔드 서비스 (NCP 최적화)
cat > /etc/systemd/system/songlab-backend.service << EOF
[Unit]
Description=SongLab Backend API
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$BACKEND_PATH
Environment=PATH=$BACKEND_PATH/venv/bin
Environment=PYTHONPATH=$BACKEND_PATH
ExecStart=$BACKEND_PATH/venv/bin/uvicorn main_v2:app --host 127.0.0.1 --port 8002 --workers 2
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=songlab-backend

# 리소스 제한
LimitNOFILE=65536
MemoryMax=1G
CPUQuota=150%

[Install]
WantedBy=multi-user.target
EOF

# 서비스 등록 및 시작
systemctl daemon-reload
systemctl enable songlab-backend
systemctl start songlab-backend

# 10. SSL 인증서 설정
echo "🔒 SSL 인증서 설정 중..."
systemctl start nginx

# Let's Encrypt 인증서 발급
certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email --non-interactive

# 11. 자동 갱신 및 백업 설정
echo "🔄 자동화 설정 중..."

# SSL 인증서 자동 갱신
crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet --nginx"; } | crontab -

# 일일 백업 스크립트
cat > /etc/cron.daily/songlab-backup << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup"

# 프로젝트 백업
tar -czf $BACKUP_DIR/songlab-$DATE.tar.gz $PROJECT_PATH $BACKEND_PATH

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "songlab-*.tar.gz" -mtime +7 -delete

# 로그 백업
journalctl -u songlab-backend --since "1 day ago" > $BACKUP_DIR/backend-$DATE.log
EOF

chmod +x /etc/cron.daily/songlab-backup

# 12. 모니터링 설정
echo "📊 모니터링 설정 중..."

# 시스템 상태 확인 스크립트
cat > /usr/local/bin/songlab-status << 'EOF'
#!/bin/bash
echo "=== SongLab 시스템 상태 ==="
echo "🕐 시간: $(date)"
echo "💾 메모리: $(free -h | awk '/^Mem:/ {print $3"/"$2}')"
echo "💽 디스크: $(df -h / | awk 'NR==2 {print $3"/"$2" ("$5")"}')"
echo "🌐 Nginx: $(systemctl is-active nginx)"
echo "🐍 Backend: $(systemctl is-active songlab-backend)"
echo "🔒 SSL: $(certbot certificates 2>/dev/null | grep "Certificate Name" | wc -l) certificates"
echo "📈 Uptime: $(uptime -p)"
EOF

chmod +x /usr/local/bin/songlab-status

# 13. 성능 최적화
echo "⚡ 성능 최적화 중..."

# 커널 매개변수 최적화
cat >> /etc/sysctl.conf << EOF
# SongLab 최적화
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 5000
vm.swappiness = 10
EOF

sysctl -p

# 14. 서비스 재시작 및 상태 확인
echo "🔄 서비스 재시작 중..."
systemctl restart nginx
systemctl restart songlab-backend

# 15. 배포 완료 확인
echo "✅ 배포 상태 확인 중..."

sleep 5

echo ""
echo "📊 시스템 상태:"
systemctl --no-pager status nginx
echo ""
systemctl --no-pager status songlab-backend
echo ""

# 16. 최종 결과
echo ""
echo "🎉 SongLab NCP 배포 완료!"
echo ""
echo "📍 접속 URL: https://$DOMAIN"
echo "📍 API URL: https://$DOMAIN/api"
echo "💰 예상 월 비용: 29,260원"
echo ""
echo "🔧 관리 명령어:"
echo "  songlab-status                          # 시스템 상태 확인"
echo "  systemctl restart songlab-backend      # 백엔드 재시작"
echo "  systemctl status nginx                 # Nginx 상태"
echo "  certbot renew                          # SSL 인증서 갱신"
echo "  tail -f /var/log/songlab/access.log    # 접속 로그"
echo ""
echo "📊 모니터링:"
echo "  htop                    # 시스템 리소스"
echo "  journalctl -u songlab-backend -f  # 백엔드 로그"
echo "  df -h                   # 디스크 사용량"
echo ""
echo "🎯 최적화 완료:"
echo "  ✅ 한국 시간대 설정"
echo "  ✅ 보안 설정 (UFW, Fail2ban)"
echo "  ✅ Rate limiting 적용"
echo "  ✅ Gzip 압축 활성화"
echo "  ✅ 자동 백업 설정"
echo "  ✅ SSL 자동 갱신"
echo ""
echo "📞 문제 발생 시: NCP 고객지원 1588-3820"