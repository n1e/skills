#!/usr/bin/env python3
# 测试7：问财人气排名测试
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import WencaiClient, HeatRank

def test_wencai_heat():
    print("=" * 50)
    print("测试7：问财人气排名")
    print("=" * 50)
    
    client = WencaiClient()
    client._init_session()
    
    print("\n查询人气排名前50")
    try:
        result = client.query("人气排名前50", perpage=50)
        datas = client._parse_answer(result)
        
        if datas:
            print(f"获取到 {len(datas)} 只股票")
            for i, item in enumerate(datas[:5]):
                print(f"  [{i+1}] {item}")
        else:
            print("未获取到数据")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == '__main__':
    test_wencai_heat()
