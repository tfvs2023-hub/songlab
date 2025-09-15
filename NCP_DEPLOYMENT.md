# SongLab 네이버 클라우드 플랫폼(NCP) 배포 가이드

## 1. NCP 서버 생성

### 1-1. 서버 인스턴스 생성
1. NCP 콘솔 접속 (https://console.ncloud.com)
2. **Server** > **Server** 메뉴 선택
3. **서버 생성** 버튼 클릭

### 1-2. 서버 설정
```
OS 이미지: Ubuntu Server 20.04 LTS
서버 타입: Standard (s-1vcpu-2GB) 또는 High CPU (c-2vcpu-4GB) 권장
스토리지: SSD 50GB
요금제: 월 정액제
```

### 1-3. 네트워크 설정
- **공인 IP 할당**: 체크
- **포트포워딩**: 22(SSH), 80(HTTP), 443(HTTPS) 허용

### 1-4. 인증키 설정
- **새 인증키 생성** 또는 기존 키 사용
- 키 파일(.pem) 다운로드 및 안전 보관

## 2. 서버 접속 및 기본 설정

### 2-1. SSH 접속
```bash
# Windows (PowerShell)
ssh -i "your-key.pem" root@서버공인IP

# 또는 PuTTY 사용
```

### 2-2. 기본 패키지 업데이트
```bash
apt update && apt upgrade -y
```

## 3. 프로젝트 배포

### 3-1. 파일 업로드 방법

#### 방법 1: SCP 사용 (권장)
```bash
# 로컬 PC에서 실행
scp -i "your-key.pem" -r C:\Users\user\Desktop\songlab root@서버IP:/tmp/
scp -i "your-key.pem" -r C:\Users\user\Desktop\songlab_advanced root@서버IP:/tmp/
```

#### 방법 2: Git 사용
```bash
# 서버에서 실행
cd /tmp
git clone https://github.com/your-username/songlab.git
```

### 3-2. 배포 스크립트 실행
```bash
# 서버에서 실행
cd /tmp/songlab
chmod +x production-deploy.sh

# 실제 도메인으로 교체
./production-deploy.sh your-domain.com your-email@example.com
```

## 4. NCP 특화 설정

### 4-1. 방화벽 설정 (ACG)
1. NCP 콘솔 > **Server** > **ACG**
2. **ACG 생성** 또는 기존 ACG 수정
3. 인바운드 규칙 추가:
   ```
   SSH: TCP 22 (0.0.0.0/0)
   HTTP: TCP 80 (0.0.0.0/0)
   HTTPS: TCP 443 (0.0.0.0/0)
   API: TCP 8002 (127.0.0.1/32) # 로컬만 허용
   ```

### 4-2. 로드밸런서 설정 (선택사항)
```bash
# 고가용성이 필요한 경우
# NCP 콘솔에서 Load Balancer 생성
# Target Group에 서버 인스턴스 추가
```

## 5. 도메인 연결

### 5-1. DNS 설정
```
A 레코드: your-domain.com → 서버 공인 IP
A 레코드: www.your-domain.com → 서버 공인 IP
```

### 5-2. SSL 인증서 설정
```bash
# 서버에서 실행
certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 6. 성능 최적화

### 6-1. NCP Object Storage 연동 (선택사항)
```python
# 대용량 파일 저장용
import boto3

s3_client = boto3.client(
    's3',
    endpoint_url='https://kr.object.ncloudstorage.com',
    access_key_id='your-access-key',
    secret_access_key='your-secret-key'
)
```

### 6-2. 모니터링 설정
```bash
# 시스템 모니터링
apt install htop iotop nethogs
```

## 7. 백업 설정

### 7-1. 스냅샷 생성
```bash
# NCP 콘솔에서 정기 스냅샷 설정
# 또는 CLI 사용
ncloud server createSnapshot --serverInstanceNo your-instance-no
```

### 7-2. 데이터 백업
```bash
# 자동 백업 스크립트
cat > /etc/cron.daily/songlab-backup << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf /backup/songlab-$DATE.tar.gz /var/www/songlab /opt/songlab-backend
find /backup -name "songlab-*.tar.gz" -mtime +7 -delete
EOF

chmod +x /etc/cron.daily/songlab-backup
```

## 8. 비용 최적화

### 8-1. 서버 크기 조정
```
개발/테스트: s-1vcpu-1GB (월 8,470원)
운영 초기: s-1vcpu-2GB (월 15,730원)
트래픽 증가 시: c-2vcpu-4GB (월 35,200원)
```

### 8-2. 스토리지 최적화
```bash
# 로그 로테이션 설정
logrotate -f /etc/logrotate.conf

# 불필요한 패키지 제거
apt autoremove -y
apt autoclean
```

## 9. 모니터링 및 알림

### 9-1. 기본 모니터링
```bash
# 리소스 사용량 확인
top
df -h
free -m
netstat -tlnp
```

### 9-2. 서비스 상태 확인
```bash
# 주요 서비스 상태
systemctl status nginx
systemctl status songlab-backend
journalctl -u songlab-backend -f
```

## 10. 트러블슈팅

### 10-1. 일반적인 문제
```bash
# 포트 확인
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
sudo netstat -tlnp | grep :8002

# 방화벽 확인
sudo ufw status
iptables -L

# 디스크 용량 확인
df -h
du -sh /var/log/*
```

### 10-2. 성능 문제
```bash
# CPU 사용률 확인
top
htop

# 메모리 사용량 확인
free -m
cat /proc/meminfo

# 네트워크 확인
ping google.com
curl -I http://localhost:8002/health
```

## 11. NCP 특별 기능 활용

### 11-1. Cloud DB for MySQL (선택사항)
```python
# 데이터베이스 분리 시
DATABASE_URL = "mysql://username:password@db-server:3306/songlab"
```

### 11-2. CDN 연동
```nginx
# Nginx 설정에 CDN 추가
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    # CDN URL로 리다이렉트
}
```

## 12. 배포 완료 체크리스트

- [ ] 서버 인스턴스 생성 완료
- [ ] SSH 접속 확인
- [ ] 프로젝트 파일 업로드
- [ ] 배포 스크립트 실행
- [ ] 도메인 DNS 설정
- [ ] SSL 인증서 설정
- [ ] 방화벽(ACG) 설정
- [ ] 서비스 정상 동작 확인
- [ ] 백업 설정
- [ ] 모니터링 설정

## 13. NCP 관련 유용한 링크

- NCP 콘솔: https://console.ncloud.com
- NCP 가이드: https://guide.ncloud-docs.com
- NCP CLI: https://cli.ncloud-docs.com
- 요금 계산기: https://www.ncloud.com/charge/calc

---

**예상 월 비용**
- 서버(s-1vcpu-2GB): 15,730원
- 공인 IP: 3,630원
- 트래픽(100GB): 9,900원
- **총합: 약 29,260원/월**

배포 중 문제가 발생하면 NCP 고객지원센터(1588-3820)로 문의하세요!