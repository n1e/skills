#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试2：大盘数据解析测试
测试涨跌统计、涨跌停数据解析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetcher.wencai import WencaiFetcher


def parse_answer(data):
    """解析问财返回数据"""
    status = data.get('errno', data.get('status_code', -1))
    if status != 0:
        print(f"  错误码: {status}")
        return []
    
    try:
        answer = data.get('data', {}).get('answer', [])
        if not answer:
            print("  answer为空")
            return []
        
        txt_list = answer[0].get('txt', [])
        if not txt_list:
            print("  txt_list为空")
            return []
        
        content = txt_list[0].get('content', {})
        components = content.get('components', [])
        if not components:
            print("  components为空")
            return []
        
        datas = components[0].get('data', {}).get('datas', [])
        return datas
    except Exception as e:
        print(f"  解析异常: {e}")
        return []


def test_market_data():
    """测试大盘数据"""
    print("=" * 50)
    print("测试2：大盘数据解析")
    print("=" * 50)
    
    client = WencaiFetcher()
    
    # 测试1：涨跌统计
    print("\n[1] 测试涨跌统计查询")
    print("    查询: 今日沪深A股涨跌统计")
    try:
        result = client.query("今日沪深A股涨跌统计")
        datas = parse_answer(result)
        
        if datas:
            item = datas[0]
            print(f"    ✅ 获取到数据!")
            print(f"    数据keys: {list(item.keys())}")
            print(f"    原始数据: {item}")
            
            up = item.get('上涨家数', item.get('上涨', 'N/A'))
            down = item.get('下跌家数', item.get('下跌', 'N/A'))
            flat = item.get('平盘家数', item.get('平盘', 'N/A'))
            print(f"    上涨: {up}, 下跌: {down}, 平盘: {flat}")
        else:
            print("    ❌ 未获取到数据")
            
    except Exception as e:
        print(f"    ❌ 查询失败: {e}")
    
    # 测试2：涨跌停数量
    print("\n[2] 测试涨跌停数量查询")
    print("    查询: 今日沪深A股涨跌停数量")
    try:
        result = client.query("今日沪深A股涨跌停数量")
        datas = parse_answer(result)
        
        if datas:
            item = datas[0]
            print(f"    ✅ 获取到数据!")
            print(f"    数据keys: {list(item.keys())}")
            print(f"    原始数据: {item}")
        else:
            print("    ❌ 未获取到数据")
            
    except Exception as e:
        print(f"    ❌ 查询失败: {e}")


if __name__ == '__main__':
    test_market_data()
    print("\n测试完成")