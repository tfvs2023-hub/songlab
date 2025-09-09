# GPU Backend 연결 가이드

## 1. RTX 5070 서버에 Docker 배포

RTX 5070 서버에서 다음 명령어를 실행하세요:

```bash
# 1. 저장소 클론
git clone [your-repository-url]
cd songlab/songlab_backend

# 2. 배포 스크립트 실행 (sudo 권한 필요)
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

배포 스크립트는 자동으로:
- NVIDIA 드라이버 확인
- Docker & NVIDIA Docker 런타임 설치
- GPU 지원 컨테이너 빌드 및 실행
- Nginx 리버스 프록시 설정

## 2. 프론트엔드 연결 설정

### 개발 환경
현재 설정: `http://localhost:8001` (로컬 백엔드)

### 프로덕션 환경
`.env.production` 파일을 수정하여 GPU 서버 IP 설정:

```bash
# GPU 서버의 실제 IP 주소로 변경
VITE_API_URL=http://192.168.1.100

# 또는 nginx 프록시 사용시
VITE_API_URL=http://your-gpu-server.com
```

## 3. 연결 상태 확인

웹 앱의 우상단에서 연결 상태를 확인할 수 있습니다:
- 🚀 GPU 서버 연결됨: 실제 GPU 분석 사용
- ⚠️ 로컬 모드 (데모): 백엔드 연결 실패시 데모 모드

## 4. 서버 관리 명령어

```bash
# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f

# 서비스 재시작
docker-compose restart

# 서비스 중지
docker-compose down

# GPU 사용량 확인
nvidia-smi
```

## 5. 트러블슈팅

### 연결이 안 될 때:
1. GPU 서버의 방화벽 설정 확인 (포트 80, 8001 열기)
2. Docker 컨테이너 상태 확인: `docker-compose ps`
3. 백엔드 헬스체크: `curl http://your-server-ip/api/health`

### GPU 인식 안 될 때:
1. NVIDIA 드라이버 설치 확인: `nvidia-smi`
2. NVIDIA Docker 런타임 확인: `docker info | grep nvidia`
3. 컨테이너 내 GPU 확인: `docker exec -it songlab-gpu-backend nvidia-smi`