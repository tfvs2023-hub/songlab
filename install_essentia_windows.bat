@echo off
REM Windows용 Essentia 설치 스크립트
REM Visual Studio Build Tools 필요

echo ===================================
echo Essentia Windows 설치 가이드
echo ===================================

echo.
echo 방법 1: Pre-built Windows 바이너리 (추천)
echo ------------------------------------------
echo 1. https://github.com/MTG/essentia/releases 접속
echo 2. essentia-2.1_beta5-win64.zip 다운로드
echo 3. 압축 해제 후 Python 경로에 추가
echo.

echo 방법 2: vcpkg 사용 (C++ 패키지 매니저)
echo ------------------------------------------
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg
.\bootstrap-vcpkg.bat
.\vcpkg integrate install
.\vcpkg install essentia
cd ..

echo.
echo 방법 3: WSL2 사용 (Linux 환경)
echo ------------------------------------------
echo wsl --install
echo wsl
echo sudo apt-get update
echo sudo apt-get install python3-essentia
echo.

echo 방법 4: Docker Desktop으로 실행
echo ------------------------------------------
echo docker pull mtgupf/essentia
echo docker run -it -v %cd%:/app mtgupf/essentia
echo.

pause
