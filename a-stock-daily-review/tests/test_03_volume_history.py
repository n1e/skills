#!/usr/bin/env python3
# 测试3：成交量历史查询测试
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import WencaiClient

def test_volume_history():
    print("=" * 50)
    print("测试3：成交量历史查询")
    print("=" * 50)
    
    client = WencaiClient()
    client._init_session()
    
    print("\n查询上证指数最近30日成交量")
    try:
        result = client.query("上证指数最近30日成交量", perpage=30)
        datas = client._parse_answer(result)
        
        if datas:
            print(f"获取到 {len(datas)} 条数据")
            for i, item in enumerate(datas[:3]):
                print(f"  [{i+1}] {item}")
        else:
            print("未获取到数据")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == '__main__':
    test_volume_history()
