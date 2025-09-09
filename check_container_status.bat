@echo off
echo Docker 컨테이너 상태 확인
echo =======================

echo.
echo 1. 컨테이너 목록:
docker ps

echo.
echo 2. 컨테이너 IP 확인:
docker inspect songlab-gpu-backend | findstr "IPAddress"

echo.
echo 3. 네트워크 정보:
docker network inspect songlab-network

echo.
echo 4. 컨테이너 로그:
docker logs songlab-gpu-backend --tail=10

echo.
echo 5. 헬스체크:
curl http://localhost:8001/api/health

echo.
pause