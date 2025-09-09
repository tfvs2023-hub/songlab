# Docker 컨테이너 IP 확인 방법

## 1. 컨테이너 실행 후 IP 확인

### 컨테이너 목록 확인:
```bash
docker ps
```

### 특정 컨테이너의 IP 확인:
```bash
# 컨테이너 이름으로 확인
docker inspect songlab-gpu-backend | grep "IPAddress"

# 또는 간단하게
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' songlab-gpu-backend
```

### Docker 네트워크 확인:
```bash
docker network ls
docker network inspect songlab-network
```

## 2. docker-compose 환경에서의 설정

현재 설정에서는:
- **컨테이너 이름**: `songlab-gpu-backend` 
- **네트워크**: `songlab-network`
- **포트**: `8001:8001` (호스트:컨테이너)

## 3. 컨테이너 간 통신

### Nginx에서 백엔드 컨테이너 접근:
```nginx
upstream backend {
    server songlab-backend:8001;  # 컨테이너 이름으로 접근
}
```

### 프론트엔드에서 접근할 때:
- **로컬 테스트**: `http://localhost:8001`
- **Docker 네트워크 내부**: `http://songlab-gpu-backend:8001`
- **외부에서 접근**: `http://HOST_IP:8001`

## 4. 실제 사용할 주소

컨테이너 실행 후:
```bash
# 1. 컨테이너 IP 직접 확인
docker inspect songlab-gpu-backend | grep "IPAddress"

# 2. 호스트를 통한 접근 (권장)
# 프론트엔드에서: http://HOST_IP:8001
```

## 5. 설정 업데이트

컨테이너 IP를 알면:
```bash
# .env.production 수정
VITE_API_URL=http://CONTAINER_IP:8001

# 또는 호스트 IP 사용 (권장)
VITE_API_URL=http://HOST_IP:8001
```