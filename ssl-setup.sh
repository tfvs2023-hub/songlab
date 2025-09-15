#!/bin/bash

# SSL 인증서 설정 스크립트
# Let's Encrypt 사용

DOMAIN="your-domain.com"
EMAIL="your-email@example.com"

echo "=== SongLab SSL 인증서 설정 ==="

# Certbot 설치 확인
if ! command -v certbot &> /dev/null; then
    echo "Certbot 설치 중..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Nginx 설정 테스트
echo "Nginx 설정 테스트 중..."
sudo nginx -t

if [ $? -ne 0 ]; then
    echo "❌ Nginx 설정에 오류가 있습니다. 먼저 수정해주세요."
    exit 1
fi

# SSL 인증서 발급
echo "SSL 인증서 발급 중..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email

if [ $? -eq 0 ]; then
    echo "✅ SSL 인증서가 성공적으로 설정되었습니다!"
    
    # 자동 갱신 테스트
    echo "자동 갱신 테스트 중..."
    sudo certbot renew --dry-run
    
    if [ $? -eq 0 ]; then
        echo "✅ 자동 갱신 설정이 완료되었습니다!"
    else
        echo "⚠️  자동 갱신 설정에 문제가 있습니다."
    fi
    
    # Nginx 재시작
    sudo systemctl restart nginx
    echo "✅ Nginx가 재시작되었습니다!"
    
else
    echo "❌ SSL 인증서 발급에 실패했습니다."
    exit 1
fi

echo "=== SSL 설정 완료 ==="
echo "도메인: https://$DOMAIN"
echo "인증서 경로: /etc/letsencrypt/live/$DOMAIN/"