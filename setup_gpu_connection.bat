@echo off
echo RTX 5070 GPU 서버 연결 설정
echo ================================

set /p GPU_IP="RTX 5070 서버의 IP 주소를 입력하세요 (예: 192.168.45.100): "

echo.
echo %GPU_IP%로 설정 중...

echo # Production GPU server configuration > .env.production
echo VITE_API_URL=http://%GPU_IP% >> .env.production

echo.
echo ✓ .env.production 파일이 업데이트되었습니다.
echo ✓ 프론트엔드에서 %GPU_IP%로 연결됩니다.
echo.
echo 다음 단계:
echo 1. RTX 5070 서버에서 Docker 배포: sudo ./deploy.sh
echo 2. 프론트엔드 재시작하여 연결 확인
echo.
pause