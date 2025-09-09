# GPU 서버 IP 주소 확인 방법

## 1. RTX 5070 서버에서 직접 확인

### Windows 서버인 경우:
```cmd
ipconfig
```
또는
```cmd
ipconfig /all
```

### Linux 서버인 경우:
```bash
ip addr show
```
또는
```bash
ifconfig
```
또는
```bash
hostname -I
```

## 2. 네트워크에서 확인

### 현재 컴퓨터에서 네트워크 스캔:
```cmd
arp -a
```

### 라우터 관리 페이지에서 확인:
- 브라우저에서 `192.168.1.1` 또는 `192.168.0.1` 접속
- 연결된 기기 목록에서 RTX 5070 서버 찾기

## 3. 일반적인 IP 주소 범위:
- `192.168.1.x` (보통 1~254)
- `192.168.0.x` (보통 1~254)
- `10.0.0.x`
- `172.16.x.x`

## 4. 확인 후 설정할 파일들:
1. `.env.production` - 프론트엔드 연결용
2. `nginx.conf` - 리버스 프록시 설정
3. `docker-compose.yml` - 포트 설정