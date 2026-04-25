#!/usr/bin/env python3
# 测试5：雪球采集器测试
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import XueqiuFetcher

def test_xueqiu():
    print("=" * 50)
    print("测试5：雪球采集器")
    print("=" * 50)
    
    fetcher = XueqiuFetcher()
    try:
        ranks = fetcher.fetch(20)
        print(f"获取到 {len(ranks)} 只股票")
        for i, r in enumerate(ranks[:5]):
            print(f"  [{i+1}] {r.code} {r.name} 热度:{r.heat_score}")
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == '__main__':
    test_xueqiu()
