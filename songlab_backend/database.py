"""
SongLab 사용자 분석 데이터 저장 시스템
SQLite 기반 로컬 데이터베이스
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import os

class SongLabDB:
    def __init__(self, db_path: str = "songlab_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 분석 결과 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            file_name TEXT,
            file_hash TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- MBTI 결과
            mbti_type_code TEXT,
            mbti_type_name TEXT,
            brightness_score INTEGER,
            thickness_score INTEGER,
            clarity_score INTEGER,
            power_score INTEGER,
            
            -- 음역 정보
            current_note TEXT,
            potential_note TEXT,
            
            -- 메타데이터
            file_size INTEGER,
            duration_seconds REAL,
            analysis_duration_ms INTEGER,
            user_ip TEXT,
            user_agent TEXT
        )
        ''')
        
        # 집계 통계 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            total_analyses INTEGER DEFAULT 0,
            unique_users INTEGER DEFAULT 0,
            avg_analysis_time REAL DEFAULT 0,
            most_common_type TEXT
        )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_upload_time ON user_analyses(upload_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mbti_type ON user_analyses(mbti_type_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON user_analyses(session_id)')
        
        conn.commit()
        conn.close()
        
        print(f"✅ 데이터베이스 초기화 완료: {self.db_path}")
    
    def generate_file_hash(self, file_content: bytes) -> str:
        """파일 해시 생성 (중복 감지용)"""
        return hashlib.md5(file_content).hexdigest()
    
    def save_analysis(self, analysis_data: Dict) -> int:
        """분석 결과 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 분석 데이터 파싱
        mbti = analysis_data.get('mbti', {})
        scores = mbti.get('scores', {})
        
        cursor.execute('''
        INSERT INTO user_analyses (
            session_id, file_name, file_hash, 
            mbti_type_code, mbti_type_name,
            brightness_score, thickness_score, clarity_score, power_score,
            current_note, potential_note,
            file_size, duration_seconds, analysis_duration_ms,
            user_ip, user_agent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis_data.get('session_id'),
            analysis_data.get('file_name'),
            analysis_data.get('file_hash'),
            analysis_data.get('mbti_type_code'),
            mbti.get('typeName'),
            scores.get('brightness', 0),
            scores.get('thickness', 0),
            scores.get('clarity', 0),
            scores.get('power', 0),
            mbti.get('currentNote'),
            mbti.get('potentialNote'),
            analysis_data.get('file_size', 0),
            analysis_data.get('duration_seconds', 0),
            analysis_data.get('analysis_duration_ms', 0),
            analysis_data.get('user_ip'),
            analysis_data.get('user_agent')
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 일별 통계 업데이트
        self.update_daily_stats()
        
        return analysis_id
    
    def update_daily_stats(self):
        """일별 통계 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 오늘의 통계 계산
        cursor.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT session_id) as unique_users,
            AVG(analysis_duration_ms) as avg_time,
            mbti_type_code,
            COUNT(mbti_type_code) as type_count
        FROM user_analyses 
        WHERE DATE(upload_time) = ?
        GROUP BY mbti_type_code
        ORDER BY type_count DESC
        LIMIT 1
        ''', (today,))
        
        result = cursor.fetchone()
        if result:
            total, unique_users, avg_time, most_common_type, _ = result
            
            cursor.execute('''
            INSERT OR REPLACE INTO daily_stats 
            (date, total_analyses, unique_users, avg_analysis_time, most_common_type)
            VALUES (?, ?, ?, ?, ?)
            ''', (today, total, unique_users, avg_time or 0, most_common_type))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        """전체 통계 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기본 통계
        cursor.execute('SELECT COUNT(*) FROM user_analyses')
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT session_id) FROM user_analyses')
        unique_users = cursor.fetchone()[0]
        
        # MBTI 타입 분포
        cursor.execute('''
        SELECT mbti_type_code, mbti_type_name, COUNT(*) as count
        FROM user_analyses 
        WHERE mbti_type_code IS NOT NULL
        GROUP BY mbti_type_code, mbti_type_name
        ORDER BY count DESC
        ''')
        mbti_distribution = [
            {'type': row[0], 'name': row[1], 'count': row[2]} 
            for row in cursor.fetchall()
        ]
        
        # 평균 점수
        cursor.execute('''
        SELECT 
            AVG(brightness_score) as avg_brightness,
            AVG(thickness_score) as avg_thickness,
            AVG(clarity_score) as avg_clarity,
            AVG(power_score) as avg_power
        FROM user_analyses
        ''')
        avg_scores = cursor.fetchone()
        
        # 최근 7일 트렌드
        cursor.execute('''
        SELECT DATE(upload_time) as date, COUNT(*) as count
        FROM user_analyses 
        WHERE upload_time >= datetime('now', '-7 days')
        GROUP BY DATE(upload_time)
        ORDER BY date
        ''')
        weekly_trend = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_analyses': total_analyses,
            'unique_users': unique_users,
            'mbti_distribution': mbti_distribution,
            'average_scores': {
                'brightness': round(avg_scores[0] or 0, 1),
                'thickness': round(avg_scores[1] or 0, 1),
                'clarity': round(avg_scores[2] or 0, 1),
                'power': round(avg_scores[3] or 0, 1)
            },
            'weekly_trend': weekly_trend
        }
    
    def export_data(self, output_file: str = None) -> str:
        """데이터 내보내기 (CSV)"""
        if not output_file:
            output_file = f"songlab_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        conn = sqlite3.connect(self.db_path)
        
        # CSV 내보내기
        import pandas as pd
        df = pd.read_sql_query('''
        SELECT 
            upload_time,
            mbti_type_code,
            mbti_type_name,
            brightness_score,
            thickness_score,
            clarity_score,
            power_score,
            current_note,
            potential_note,
            file_size,
            duration_seconds
        FROM user_analyses
        ORDER BY upload_time DESC
        ''', conn)
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        conn.close()
        
        return output_file
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """오래된 데이터 정리"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        DELETE FROM user_analyses 
        WHERE upload_time < datetime('now', '-{} days')
        '''.format(days_to_keep))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"🧹 {deleted_count}개의 오래된 레코드 삭제됨")
        return deleted_count


# FastAPI에 통합할 함수들
def init_database():
    """데이터베이스 초기화 (FastAPI 시작시 호출)"""
    db = SongLabDB()
    return db

def save_user_analysis(db: SongLabDB, result: Dict, metadata: Dict) -> int:
    """사용자 분석 결과 저장"""
    analysis_data = {
        'session_id': metadata.get('session_id'),
        'file_name': metadata.get('file_name'),
        'file_hash': metadata.get('file_hash'),
        'mbti_type_code': get_mbti_type_code(result.get('mbti', {})),
        'file_size': metadata.get('file_size', 0),
        'duration_seconds': metadata.get('duration_seconds', 0),
        'analysis_duration_ms': metadata.get('analysis_duration_ms', 0),
        'user_ip': metadata.get('user_ip'),
        'user_agent': metadata.get('user_agent'),
        'mbti': result.get('mbti', {})
    }
    
    return db.save_analysis(analysis_data)

def get_mbti_type_code(mbti_data: Dict) -> str:
    """MBTI 데이터에서 타입 코드 추출"""
    scores = mbti_data.get('scores', {})
    type_code = ''
    type_code += 'D' if scores.get('brightness', 0) < 0 else 'B'
    type_code += 'K' if scores.get('thickness', 0) > 0 else 'N'
    type_code += 'C' if scores.get('clarity', 0) > 0 else 'R'
    type_code += 'S' if scores.get('power', 0) > 0 else 'W'
    return type_code


if __name__ == "__main__":
    # 테스트
    db = SongLabDB()
    
    # 샘플 데이터 생성
    sample_result = {
        'mbti': {
            'typeName': '카리스마틱 보컬',
            'scores': {'brightness': -65, 'thickness': 75, 'clarity': 45, 'power': 82},
            'currentNote': '3옥타브 파#',
            'potentialNote': '4옥타브 라'
        }
    }
    
    sample_metadata = {
        'session_id': 'test_session_123',
        'file_name': 'test_voice.wav',
        'file_hash': 'abc123def456',
        'file_size': 1024000,
        'duration_seconds': 15.3,
        'analysis_duration_ms': 5000,
        'user_ip': '127.0.0.1',
        'user_agent': 'TestBrowser/1.0'
    }
    
    # 데이터 저장 테스트
    analysis_id = save_user_analysis(db, sample_result, sample_metadata)
    print(f"📝 분석 저장 완료 (ID: {analysis_id})")
    
    # 통계 조회
    stats = db.get_statistics()
    print(f"📊 총 분석: {stats['total_analyses']}건")
    print(f"👥 사용자: {stats['unique_users']}명")