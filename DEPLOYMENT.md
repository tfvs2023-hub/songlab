# SongLab 프로덕션 배포 가이드

## 개요
SongLab을 도메인에 배포하기 위한 완전한 가이드입니다.

## 사전 요구사항

### 1. 서버 준비
- Ubuntu 20.04 LTS 이상 권장
- 최소 사양: CPU 2코어, RAM 4GB, 디스크 50GB
- 권장 사양: CPU 4코어, RAM 8GB, 디스크 100GB
- 도메인 등록 및 DNS 설정 완료

### 2. 도메인 설정
```bash
# DNS A 레코드 설정
your-domain.com     → 서버 IP 주소
www.your-domain.com → 서버 IP 주소
```

## 자동 배포 (권장)

### 1. 서버에 파일 업로드
```bash
# 로컬에서 서버로 파일 전송
scp -r songlab/ user@your-server:/tmp/
ssh user@your-server
cd /tmp/songlab
```

### 2. 배포 스크립트 실행
```bash
chmod +x production-deploy.sh
sudo ./production-deploy.sh your-domain.com your-email@example.com
```

## 수동 배포

### 1. 시스템 패키지 설치
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx python3 python3-pip python3-venv nodejs npm git
```

### 2. 프로젝트 디렉토리 설정
```bash
sudo mkdir -p /var/www/songlab
sudo mkdir -p /opt/songlab-backend
sudo chown -R $USER:$USER /var/www/songlab
sudo chown -R $USER:$USER /opt/songlab-backend
```

### 3. 백엔드 설정
```bash
cd /opt/songlab-backend

# 백엔드 파일 복사
cp -r /path/to/songlab_advanced/* .

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install fastapi uvicorn python-multipart soundfile scipy parselmouth python-dotenv google-api-python-client requests onnxruntime
```

### 4. 프론트엔드 빌드
```bash
cd /var/www/songlab

# 프론트엔드 파일 복사
cp -r /path/to/songlab/* .

# 프로덕션 환경변수 설정
cat > .env.production << EOF
VITE_API_URL=https://your-domain.com/api
NODE_ENV=production
EOF

# 빌드
npm install
npm run build
```

### 5. Nginx 설정
```bash
# 설정 파일 복사
sudo cp nginx.conf /etc/nginx/sites-available/songlab

# 도메인 설정 업데이트
sudo sed -i 's/your-domain.com/실제도메인.com/g' /etc/nginx/sites-available/songlab

# 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/songlab /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 설정 테스트
sudo nginx -t
```

### 6. SSL 인증서 설정
```bash
# Certbot 설치
sudo apt install -y certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 7. 시스템 서비스 생성
```bash
# 백엔드 서비스 설정
sudo tee /etc/systemd/system/songlab-backend.service > /dev/null << EOF
[Unit]
Description=SongLab Backend API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/songlab-backend
Environment=PATH=/opt/songlab-backend/venv/bin
ExecStart=/opt/songlab-backend/venv/bin/uvicorn main_v2:app --host 127.0.0.1 --port 8002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable songlab-backend
sudo systemctl start songlab-backend
```

### 8. 방화벽 설정
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw --force enable
```

## 운영 관리

### 주요 명령어
```bash
# 서비스 상태 확인
sudo systemctl status songlab-backend
sudo systemctl status nginx

# 서비스 재시작
sudo systemctl restart songlab-backend
sudo systemctl restart nginx

# 로그 확인
sudo journalctl -u songlab-backend -f
sudo tail -f /var/log/nginx/songlab_access.log
sudo tail -f /var/log/nginx/songlab_error.log

# SSL 인증서 갱신
sudo certbot renew
```

### 모니터링
```bash
# 시스템 리소스 확인
top
df -h
free -m

# 네트워크 연결 확인
sudo netstat -tlnp | grep :8002
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

### 백업
```bash
# 데이터베이스 백업 (PostgreSQL 사용 시)
sudo -u postgres pg_dump songlab > backup_$(date +%Y%m%d).sql

# 설정 파일 백업
tar -czf backup_config_$(date +%Y%m%d).tar.gz /etc/nginx/sites-available/songlab /opt/songlab-backend /var/www/songlab
```

### 업데이트
```bash
# 백엔드 코드 업데이트
cd /opt/songlab-backend
git pull  # 또는 파일 복사
sudo systemctl restart songlab-backend

# 프론트엔드 코드 업데이트
cd /var/www/songlab
npm run build
sudo systemctl reload nginx
```

## 트러블슈팅

### 일반적인 문제

1. **502 Bad Gateway**
   ```bash
   # 백엔드 서비스 상태 확인
   sudo systemctl status songlab-backend
   sudo journalctl -u songlab-backend -n 50
   ```

2. **SSL 인증서 문제**
   ```bash
   # 인증서 상태 확인
   sudo certbot certificates
   # 갱신 시도
   sudo certbot renew --dry-run
   ```

3. **포트 충돌**
   ```bash
   # 포트 사용 확인
   sudo lsof -i :8002
   sudo lsof -i :80
   sudo lsof -i :443
   ```

4. **디스크 부족**
   ```bash
   # 디스크 사용량 확인
   df -h
   # 로그 파일 정리
   sudo journalctl --vacuum-time=7d
   ```

### 로그 분석
```bash
# 에러 로그 실시간 모니터링
sudo tail -f /var/log/nginx/songlab_error.log | grep -E "(error|warn)"

# 백엔드 에러 확인
sudo journalctl -u songlab-backend --since "1 hour ago" | grep -E "(ERROR|WARNING)"
```

## 성능 최적화

### Nginx 최적화
```nginx
# /etc/nginx/nginx.conf에 추가
worker_processes auto;
worker_connections 1024;

# Gzip 압축
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

# 캐시 설정
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 시스템 최적화
```bash
# 파일 디스크립터 제한 증가
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

## 보안 체크리스트

- [ ] SSH 키 기반 인증 설정
- [ ] 불필요한 포트 차단
- [ ] 정기적인 시스템 업데이트
- [ ] SSL 인증서 자동 갱신 설정
- [ ] 로그 모니터링 설정
- [ ] 백업 자동화
- [ ] 방화벽 설정 확인

## 연락처 및 지원

문제 발생 시:
1. 로그 파일 확인
2. 시스템 리소스 확인
3. 서비스 상태 확인
4. 필요시 전문가 상담

---

**배포 완료 후 확인사항:**
- [ ] https://your-domain.com 접속 확인
- [ ] 보컬 분석 기능 테스트
- [ ] YouTube 추천 기능 확인
- [ ] 모바일 접속 테스트
- [ ] SSL 인증서 상태 확인