"""
SongLab 광고 시스템
Google AdSense, 자체 광고 관리 및 수익화
"""

import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class AdSystem:
    def __init__(self, db_path="songlab_data.db"):
        self.db_path = db_path
        self.init_ad_tables()
    
    def init_ad_tables(self):
        """광고 관련 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 광고 캠페인 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- 'banner', 'interstitial', 'video', 'native'
            content TEXT, -- HTML 또는 이미지 URL
            target_audience TEXT, -- JSON: {"age": "20-30", "gender": "all", "interests": []}
            start_date DATE,
            end_date DATE,
            is_active BOOLEAN DEFAULT TRUE,
            priority INTEGER DEFAULT 1,
            click_url TEXT,
            impression_count INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            revenue_per_click REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 광고 노출 로그
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_impressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            user_id INTEGER,
            session_id TEXT,
            ad_position TEXT, -- 'pre_analysis', 'post_analysis', 'sidebar'
            shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicked BOOLEAN DEFAULT FALSE,
            clicked_at TIMESTAMP,
            user_ip TEXT,
            user_agent TEXT,
            FOREIGN KEY (campaign_id) REFERENCES ad_campaigns (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Google AdSense 설정
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ad_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 기본 설정 삽입
        cursor.execute('''
        INSERT OR IGNORE INTO ad_settings (key, value) VALUES
        ('adsense_client_id', 'ca-pub-your-adsense-id'),
        ('ad_frequency', '3'), -- 몇 번에 한 번 광고 표시
        ('premium_users_ads', 'false'), -- 프리미엄 유저에게 광고 표시 여부
        ('ad_positions', '["pre_analysis", "post_analysis"]')
        ''')
        
        conn.commit()
        conn.close()
    
    def get_ad_for_position(self, position: str, user_id: Optional[int] = None, session_id: str = None) -> Optional[Dict]:
        """특정 위치에 표시할 광고 선택"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자가 프리미엄인지 확인
        if user_id:
            cursor.execute('SELECT is_premium FROM users WHERE id = ?', (user_id,))
            user_row = cursor.fetchone()
            if user_row and user_row[0]:  # 프리미엄 유저
                cursor.execute('SELECT value FROM ad_settings WHERE key = ?', ('premium_users_ads',))
                setting = cursor.fetchone()
                if setting and setting[0].lower() == 'false':
                    return None  # 프리미엄 유저에게는 광고 미표시
        
        # 광고 빈도 확인
        cursor.execute('SELECT value FROM ad_settings WHERE key = ?', ('ad_frequency',))
        frequency_setting = cursor.fetchone()
        frequency = int(frequency_setting[0]) if frequency_setting else 3
        
        if random.randint(1, frequency) != 1:  # 설정된 빈도에 따라 광고 표시
            return None
        
        # 활성 광고 캠페인 조회
        cursor.execute('''
        SELECT * FROM ad_campaigns 
        WHERE is_active = TRUE 
        AND (start_date IS NULL OR start_date <= DATE('now'))
        AND (end_date IS NULL OR end_date >= DATE('now'))
        ORDER BY priority DESC, RANDOM()
        LIMIT 1
        ''')
        
        campaign = cursor.fetchone()
        if not campaign:
            conn.close()
            return self.get_default_ad(position)
        
        # 광고 노출 로그 기록
        cursor.execute('''
        INSERT INTO ad_impressions (campaign_id, user_id, session_id, ad_position, user_ip)
        VALUES (?, ?, ?, ?, ?)
        ''', (campaign[0], user_id, session_id, position, '127.0.0.1'))  # IP는 실제 구현시 request에서 가져옴
        
        # 노출 횟수 증가
        cursor.execute('''
        UPDATE ad_campaigns SET impression_count = impression_count + 1
        WHERE id = ?
        ''', (campaign[0],))
        
        conn.commit()
        conn.close()
        
        # 광고 데이터 반환
        return {
            'id': campaign[0],
            'type': campaign[2],
            'content': campaign[3],
            'click_url': campaign[9],
            'position': position
        }
    
    def get_default_ad(self, position: str) -> Dict:
        """기본 광고 (자체 광고 또는 AdSense)"""
        # Google AdSense 광고 코드 생성
        adsense_ads = {
            'pre_analysis': {
                'type': 'adsense',
                'content': '''
                <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-your-id"></script>
                <ins class="adsbygoogle"
                     style="display:block"
                     data-ad-client="ca-pub-your-id"
                     data-ad-slot="1234567890"
                     data-ad-format="auto"
                     data-full-width-responsive="true"></ins>
                <script>
                     (adsbygoogle = window.adsbygoogle || []).push({});
                </script>
                ''',
                'position': position
            },
            'post_analysis': {
                'type': 'adsense',
                'content': '''
                <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-your-id"></script>
                <ins class="adsbygoogle"
                     style="display:block; text-align:center;"
                     data-ad-layout="in-article"
                     data-ad-format="fluid"
                     data-ad-client="ca-pub-your-id"
                     data-ad-slot="0987654321"></ins>
                <script>
                     (adsbygoogle = window.adsbygoogle || []).push({});
                </script>
                ''',
                'position': position
            }
        }
        
        # 자체 광고 (SongLab 프리미엄, 음성 코칭 등)
        self_ads = [
            {
                'type': 'native',
                'content': '''
                <div class="songlab-premium-ad" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; color: white; text-align: center;">
                    <h3>🎤 SongLab Premium</h3>
                    <p>무제한 분석 + 상세 피드백 + 광고 없는 경험</p>
                    <button style="background: white; color: #667eea; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: pointer;">
                        7일 무료 체험 시작
                    </button>
                </div>
                ''',
                'click_url': '/premium',
                'position': position
            },
            {
                'type': 'banner',
                'content': '''
                <div class="vocal-coaching-ad" style="background: #FF6B6B; padding: 15px; border-radius: 8px; color: white; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <strong>🎵 1:1 보컬 코칭</strong>
                        <p style="margin: 5px 0;">전문 코치와 함께하는 맞춤 레슨</p>
                    </div>
                    <button style="background: white; color: #FF6B6B; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold;">
                        상담 신청
                    </button>
                </div>
                ''',
                'click_url': '/coaching',
                'position': position
            }
        ]
        
        # AdSense 광고가 있으면 70% 확률로 표시, 없으면 자체 광고
        if position in adsense_ads and random.random() < 0.7:
            return adsense_ads[position]
        else:
            return random.choice(self_ads)
    
    def record_ad_click(self, impression_id: int):
        """광고 클릭 기록"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 클릭 기록 업데이트
        cursor.execute('''
        UPDATE ad_impressions 
        SET clicked = TRUE, clicked_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (impression_id,))
        
        # 캠페인 클릭 수 증가
        cursor.execute('''
        UPDATE ad_campaigns 
        SET click_count = click_count + 1
        WHERE id = (SELECT campaign_id FROM ad_impressions WHERE id = ?)
        ''', (impression_id,))
        
        conn.commit()
        conn.close()
    
    def get_ad_stats(self) -> Dict:
        """광고 통계"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 전체 통계
        cursor.execute('''
        SELECT 
            COUNT(*) as total_impressions,
            SUM(CASE WHEN clicked = TRUE THEN 1 ELSE 0 END) as total_clicks,
            COUNT(DISTINCT session_id) as unique_viewers
        FROM ad_impressions 
        WHERE shown_at >= datetime('now', '-30 days')
        ''')
        overall_stats = cursor.fetchone()
        
        # 캠페인별 통계
        cursor.execute('''
        SELECT 
            c.name,
            c.impression_count,
            c.click_count,
            ROUND((c.click_count * 100.0 / NULLIF(c.impression_count, 0)), 2) as ctr,
            c.revenue_per_click * c.click_count as revenue
        FROM ad_campaigns c
        WHERE c.impression_count > 0
        ORDER BY c.impression_count DESC
        ''')
        campaign_stats = cursor.fetchall()
        
        # 일별 트렌드
        cursor.execute('''
        SELECT 
            DATE(shown_at) as date,
            COUNT(*) as impressions,
            SUM(CASE WHEN clicked = TRUE THEN 1 ELSE 0 END) as clicks
        FROM ad_impressions 
        WHERE shown_at >= datetime('now', '-7 days')
        GROUP BY DATE(shown_at)
        ORDER BY date
        ''')
        daily_stats = cursor.fetchall()
        
        conn.close()
        
        ctr = (overall_stats[1] / overall_stats[0] * 100) if overall_stats[0] > 0 else 0
        
        return {
            'overview': {
                'total_impressions': overall_stats[0],
                'total_clicks': overall_stats[1],
                'unique_viewers': overall_stats[2],
                'ctr_percentage': round(ctr, 2)
            },
            'campaigns': [
                {
                    'name': row[0], 
                    'impressions': row[1], 
                    'clicks': row[2], 
                    'ctr': row[3], 
                    'revenue': row[4]
                } 
                for row in campaign_stats
            ],
            'daily_trend': [
                {'date': row[0], 'impressions': row[1], 'clicks': row[2]} 
                for row in daily_stats
            ]
        }
    
    def create_campaign(self, campaign_data: Dict) -> int:
        """새 광고 캠페인 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO ad_campaigns (name, type, content, target_audience, start_date, end_date, 
                                  priority, click_url, revenue_per_click)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            campaign_data['name'],
            campaign_data['type'],
            campaign_data['content'],
            json.dumps(campaign_data.get('target_audience', {})),
            campaign_data.get('start_date'),
            campaign_data.get('end_date'),
            campaign_data.get('priority', 1),
            campaign_data.get('click_url'),
            campaign_data.get('revenue_per_click', 0.0)
        ))
        
        campaign_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return campaign_id


# 광고 시스템 인스턴스
ad_system = AdSystem()

if __name__ == "__main__":
    # 테스트 캠페인 생성
    ad_system = AdSystem()
    
    sample_campaign = {
        'name': '보컬 레슨 프로모션',
        'type': 'banner',
        'content': '<div>음성 분석 후 1:1 코칭을 받아보세요!</div>',
        'click_url': '/coaching',
        'priority': 5,
        'revenue_per_click': 0.10
    }
    
    campaign_id = ad_system.create_campaign(sample_campaign)
    print(f"✅ 테스트 캠페인 생성 완료 (ID: {campaign_id})")
    
    # 광고 테스트
    ad = ad_system.get_ad_for_position('pre_analysis', session_id='test123')
    if ad:
        print(f"🎯 광고 선택됨: {ad['type']}")
    else:
        print("❌ 표시할 광고 없음")
    
    # 통계 확인
    stats = ad_system.get_ad_stats()
    print(f"📊 광고 통계: {stats['overview']['total_impressions']}회 노출")