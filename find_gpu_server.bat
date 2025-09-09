@echo off
echo RTX 5070 GPU 서버 찾기...
echo.

echo 일반적인 IP 주소들을 ping으로 확인:
for %%i in (100 101 102 110 111 200 201 210) do (
    echo Testing 192.168.45.%%i...
    ping -n 1 -w 1000 192.168.45.%%i >nul
    if !errorlevel! equ 0 (
        echo ✓ 192.168.45.%%i 응답함
    ) else (
        echo ✗ 192.168.45.%%i 응답없음
    )
)

echo.
echo RTX 5070 서버에서 직접 확인하세요:
echo Windows: ipconfig
echo Linux: ip addr 또는 hostname -I