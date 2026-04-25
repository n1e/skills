#!/usr/bin/env python3
# 测试4：涨停股票采集测试
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import WencaiClient

def test_surge_stocks():
    print("=" * 50)
    print("测试4：涨停股票采集")
    print("=" * 50)
    
    client = WencaiClient()
    client._init_session()
    
    print("\n查询今日涨停股")
    try:
        stocks = client.get_surge_stocks()
        print(f"获取到 {len(stocks)} 只涨停股")
        for i, s in enumerate(stocks[:5]):
            print(f"  [{i+1}] {s.code} {s.name} 涨{s.change_pct}% 原因:{s.reason[:30]}")
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == '__main__':
    test_surge_stocks()
