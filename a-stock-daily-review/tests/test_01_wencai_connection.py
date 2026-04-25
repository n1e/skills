#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试1：问财连接测试
测试问财API是否可访问
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import random
import string
import subprocess
import urllib.parse
import requests


def rand_string(n: int) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def find_hexin_v_js():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 向上找两层到主目录
    js_path = os.path.join(script_dir, '..', 'lib', 'hexin_v.js')
    if os.path.exists(js_path):
        return js_path
    return 'lib/hexin_v.js'


def generate_hexin_v():
    timestamp = f"{time.time():.3f}"
    js_path = find_hexin_v_js()
    try:
        result = subprocess.run(
            ['node', js_path, timestamp],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"生成Hexin-V失败: {e}")
        return "default_hexin_v_value"


def test_wencai_connection():
    """测试问财连接"""
    print("=" * 50)
    print("测试1：问财连接测试")
    print("=" * 50)
    
    session = requests.Session()
    other_uid = f"Ths_iwencai_Xuangu_{rand_string(32)}"
    cookies = {
        'other_uid': other_uid,
        'ta_random_userid': rand_string(10),
        'v': ''
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    # 1. 访问主页
    print("\n[1] 访问问财主页...")
    try:
        resp = session.get('https://www.iwencai.com', headers=headers, timeout=15)
        print(f"    状态码: {resp.status_code}")
        for cookie in resp.cookies:
            cookies[cookie.name] = cookie.value
        print(f"    获取cookies: {list(cookies.keys())}")
    except Exception as e:
        print(f"    ❌ 失败: {e}")
        return False
    
    time.sleep(0.5)
    
    # 2. 访问搜索页
    print("\n[2] 访问搜索页...")
    try:
        resp = session.get('https://www.iwencai.com/unifiedwap/home/index', headers=headers, timeout=15)
        print(f"    状态码: {resp.status_code}")
        for cookie in resp.cookies:
            cookies[cookie.name] = cookie.value
    except Exception as e:
        print(f"    ❌ 失败: {e}")
        return False
    
    time.sleep(0.5)
    
    # 3. 初始化会话
    print("\n[3] 初始化会话...")
    hexin_v = generate_hexin_v()
    cookies['v'] = hexin_v
    print(f"    Hexin-V: {hexin_v[:20]}...")
    
    hint_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.iwencai.com',
        'Referer': 'https://www.iwencai.com/unifiedwap/home/index',
        'Hexin-V': hexin_v,
    }
    try:
        resp = session.post(
            'https://www.iwencai.com/unifiedwap/suggest/V1/index/query-hint-list',
            headers=hint_headers,
            data={'dataType': 'history', 'isAll': '1', 'num': '20', 'queryType': 'index', 'relatedId': ''},
            cookies=cookies,
            timeout=15
        )
        print(f"    状态码: {resp.status_code}")
    except Exception as e:
        print(f"    ❌ 失败: {e}")
        return False
    
    # 4. 测试查询
    print("\n[4] 测试查询（简单问题）...")
    hexin_v = generate_hexin_v()
    cookies['v'] = hexin_v
    
    payload = {
        "source": "Ths_iwencai_Xuangu",
        "version": "2.0",
        "query_area": "",
        "block_list": "",
        "add_info": '{"urp":{"scene":1,"company":1,"business":1},"contentType":"json","searchInfo":true}',
        "question": "上证指数",
        "perpage": 5,
        "page": 1,
        "secondary_intent": "",
        "log_info": '{"input_type":"typewrite"}',
        "rsh": other_uid,
    }
    
    query_headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.iwencai.com',
        'Referer': 'https://www.iwencai.com/unifiedwap/result?w=%E4%B8%8A%E8%AF%81%E6%8C%87%E6%95%B0',
        'Hexin-V': hexin_v,
    }
    
    try:
        resp = session.post(
            'https://www.iwencai.com/customized/chart/get-robot-data',
            headers=query_headers,
            json=payload,
            cookies=cookies,
            timeout=30
        )
        print(f"    状态码: {resp.status_code}")
        
        data = resp.json()
        # 检查状态：errno 或 status_code 或 data.status_code
        errno = data.get('errno')
        status_code = data.get('status_code', data.get('data', {}).get('status_code'))
        print(f"    响应状态: errno={errno}, status_code={status_code}")
        
        if data.get('errno') == 0:
            print("    ✅ 问财连接成功!")
            print(f"    数据keys: {list(data.get('data', {}).keys())}")
            return True
        else:
            print(f"    ❌ 问财返回错误: {data}")
            return False
            
    except Exception as e:
        print(f"    ❌ 查询失败: {e}")
        return False


if __name__ == '__main__':
    success = test_wencai_connection()
    print("\n" + "=" * 50)
    if success:
        print("✅ 测试通过：问财连接正常")
    else:
        print("❌ 测试失败：问财连接异常")
    print("=" * 50)