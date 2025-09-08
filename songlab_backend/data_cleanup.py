"""
데이터 정리 및 비용 최적화 시스템
오래된 데이터 삭제, 압축, 백업 관리
"""

import sqlite3
import os
import gzip
import json
from datetime import datetime, timedelta
from database import SongLabDB

class DataManager:
    def __init__(self, db_path="songlab_data.db"):
        self.db = SongLabDB(db_path)
        self.db_path = db_path
    
    def optimize_storage(self):
        """스토리지 최적화"""
        print("📊 데이터 최적화 시작...")
        
        # 1. 오래된 상세 데이터 삭제 (3개월)
        deleted = self.cleanup_old_data(days=90)
        
        # 2. 중복 데이터 제거
        duplicates = self.remove_duplicates()
        
        # 3. 데이터베이스 VACUUM (빈 공간 정리)
        self.vacuum_database()
        
        # 4. 파일 크기 확인
        file_size = self.get_db_size()
        
        print(f"✅ 최적화 완료:")
        print(f"   삭제된 레코드: {deleted}개")
        print(f"   중복 제거: {duplicates}개")
        print(f"   현재 DB 크기: {file_size:.2f}MB")
        
        return {
            'deleted_records': deleted,
            'removed_duplicates': duplicates,
            'db_size_mb': file_size
        }
    
    def cleanup_old_data(self, days=90):
        """오래된 데이터 삭제"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 3개월 이상 된 데이터 삭제
        cursor.execute('''
        DELETE FROM user_analyses 
        WHERE upload_time < datetime('now', '-{} days')
        '''.format(days))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def remove_duplicates(self):
        """중복 데이터 제거 (같은 파일 해시)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 중복 제거 (최신 것만 유지)
        cursor.execute('''
        DELETE FROM user_analyses 
        WHERE id NOT IN (
            SELECT MAX(id) 
            FROM user_analyses 
            GROUP BY file_hash
        )
        ''')
        
        removed_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return removed_count
    
    def vacuum_database(self):
        """데이터베이스 압축"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('VACUUM')
        conn.close()
    
    def get_db_size(self):
        """DB 파일 크기 (MB)"""
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path) / (1024 * 1024)
        return 0
    
    def export_and_compress(self, backup_path="backup"):
        """데이터 압축 백업"""
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        
        # 현재 날짜로 백업 파일명
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_path}/songlab_backup_{timestamp}.json.gz"
        
        # 데이터 추출
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM user_analyses 
        ORDER BY upload_time DESC
        ''')
        
        # JSON으로 변환
        columns = [description[0] for description in cursor.description]
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(columns, row)))
        
        conn.close()
        
        # 압축 저장
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        
        # 압축률 계산
        original_size = self.get_db_size()
        compressed_size = os.path.getsize(backup_file) / (1024 * 1024)
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        print(f"📦 백업 완료: {backup_file}")
        print(f"   원본: {original_size:.2f}MB → 압축: {compressed_size:.2f}MB")
        print(f"   압축률: {compression_ratio:.1f}%")
        
        return backup_file
    
    def get_storage_stats(self):
        """스토리지 통계"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 전체 레코드 수
        cursor.execute('SELECT COUNT(*) FROM user_analyses')
        total_records = cursor.fetchone()[0]
        
        # 월별 데이터량
        cursor.execute('''
        SELECT 
            strftime('%Y-%m', upload_time) as month,
            COUNT(*) as count,
            AVG(file_size) as avg_file_size
        FROM user_analyses 
        GROUP BY strftime('%Y-%m', upload_time)
        ORDER BY month DESC
        LIMIT 12
        ''')
        
        monthly_data = cursor.fetchall()
        
        # 예상 월 증가량
        if len(monthly_data) >= 2:
            recent_avg = (monthly_data[0][1] + monthly_data[1][1]) / 2
        else:
            recent_avg = monthly_data[0][1] if monthly_data else 0
        
        conn.close()
        
        # 현재 크기 및 예상 증가량
        current_size = self.get_db_size()
        estimated_monthly_growth = (recent_avg * 0.05)  # 레코드당 약 50KB
        
        return {
            'total_records': total_records,
            'current_db_size_mb': current_size,
            'estimated_monthly_growth_mb': estimated_monthly_growth,
            'estimated_yearly_cost_usd': estimated_monthly_growth * 12 * 0.10 / 1024,  # AWS EBS 비용
            'monthly_breakdown': [
                {'month': row[0], 'records': row[1], 'avg_file_size': row[2]}
                for row in monthly_data
            ]
        }


def setup_auto_cleanup():
    """자동 정리 설정 (cron job용)"""
    manager = DataManager()
    
    # 매주 정리
    print("🔄 주간 자동 정리 시작...")
    stats = manager.optimize_storage()
    
    # 매월 백업
    if datetime.now().day == 1:  # 매월 1일
        print("📦 월간 백업 시작...")
        manager.export_and_compress()
    
    return stats


if __name__ == "__main__":
    manager = DataManager()
    
    print("=" * 50)
    print("💾 SongLab 데이터 관리 시스템")
    print("=" * 50)
    
    # 현재 스토리지 상태
    stats = manager.get_storage_stats()
    print(f"📊 현재 상태:")
    print(f"   총 레코드: {stats['total_records']:,}개")
    print(f"   DB 크기: {stats['current_db_size_mb']:.2f}MB")
    print(f"   월 예상 증가: {stats['estimated_monthly_growth_mb']:.2f}MB")
    print(f"   년 예상 비용: ${stats['estimated_yearly_cost_usd']:.2f}")
    
    # 최적화 실행
    print(f"\n🛠️  최적화 실행:")
    result = manager.optimize_storage()
    
    print(f"\n💡 비용 절약 팁:")
    print(f"   • 90일 이상 된 데이터 자동 삭제")
    print(f"   • 중복 파일 자동 제거") 
    print(f"   • 압축 백업으로 90% 용량 절약")
    print(f"   • 실제 서버 비용: 월 $1 이하 예상")