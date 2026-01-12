#!/usr/bin/env python3
"""clusters 테이블 내용 확인"""
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.db_queries import get_db_connection
import pandas as pd

conn = get_db_connection()
if conn:
    try:
        # 테이블 구조 확인
        print('=' * 80)
        print('clusters 테이블 구조')
        print('=' * 80)
        df_schema = pd.read_sql_query("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'clusters'
            ORDER BY ordinal_position
        """, conn)
        print(df_schema.to_string())
        
        print('\n' + '=' * 80)
        print('clusters 테이블 데이터 (전체)')
        print('=' * 80)
        df_data = pd.read_sql_query("""
            SELECT 
                cluster_id,
                size,
                algorithm,
                topic_category,
                sub_cluster_index,
                top_keywords,
                noise_label,
                created_at
            FROM clusters
            ORDER BY cluster_id
        """, conn)
        print(f'총 {len(df_data)}개 행')
        print(df_data.to_string())
        
        # topic_category별 통계
        print('\n' + '=' * 80)
        print('topic_category별 통계')
        print('=' * 80)
        df_stats = pd.read_sql_query("""
            SELECT 
                topic_category,
                COUNT(*) as cluster_count,
                SUM(size) as total_size
            FROM clusters
            WHERE noise_label = FALSE
            GROUP BY topic_category
            ORDER BY topic_category
        """, conn)
        print(df_stats.to_string())
        
    except Exception as e:
        print(f'에러: {e}')
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
else:
    print('DB 연결 실패')
