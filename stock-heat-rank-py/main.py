#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票热度排名采集器 - Python版
A-Share Heat Rank Collector - Python Version

采集问财、雪球、东方财富三大平台人气榜单，计算复合热度分数

问财数据仅使用 OpenAPI 方式获取
旧 URL 方式已移除，因为接口已过期
需要配置 IWENCAI_API_KEY 环境变量
"""

import argparse
import gzip
import json
import os
import random
import re
import string
import sys
import time
import urllib.parse
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import requests


def get_api_key() -> str:
    """获取问财 API Key
    
    优先从环境变量读取
    """
    return os.environ.get('IWENCAI_API_KEY', '')


def check_api_key_configured() -> bool:
    """检查 API Key 是否已配置
    
    Returns:
        True 如果已配置，False 否则
    """
    api_key = get_api_key()
    if not api_key:
        return False
    if api_key == 'sk-proj-00':
        return False
    return True


def get_api_key_reminder() -> str:
    """获取 API Key 配置提醒信息"""
    return """
⚠️  问财 API Key 未配置！

需要配置 IWENCAI_API_KEY 环境变量才能使用问财人气排名查询功能。

配置方式：
1. Windows (CMD):
   set IWENCAI_API_KEY=your_api_key_here

2. Windows (PowerShell):
   $env:IWENCAI_API_KEY="your_api_key_here"

3. Linux/Mac:
   export IWENCAI_API_KEY=your_api_key_here

获取 API Key：请访问同花顺问财开放平台申请
"""


@dataclass
class StockRank:
    """股票排名信息"""
    code: str
    name: str
    rank: int
    heat_score: int
    source: str


@dataclass
class CompositeRank:
    """复合排名"""
    code: str
    name: str = ""
    wencai_rank: int = 0
    xueqiu_rank: int = 0
    eastmoney_rank: int = 0
    composite_score: float = 0.0
    appear_count: int = 0


def rand_string(n: int) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


class WencaiOpenAPI:
    """
    问财官方 OpenAPI 客户端
    
    使用 https://openapi.iwencai.com/v1/query2data 进行数据查询
    这是当前唯一支持的方式
    """
    
    DEFAULT_API_URL = "https://openapi.iwencai.com/v1/query2data"
    DEFAULT_PAGE = "1"
    DEFAULT_LIMIT = "50"
    DEFAULT_IS_CACHE = "1"
    DEFAULT_EXPAND_INDEX = "true"
    
    def __init__(self):
        self._api_key = get_api_key()
        self._available = None
    
    def _check_available(self) -> bool:
        """检查 OpenAPI 是否可用"""
        if self._available is not None:
            return self._available
        
        if not self._api_key:
            print("  [警告] IWENCAI_API_KEY 未配置，OpenAPI 不可用")
            self._available = False
            return False
        
        if self._api_key == 'sk-proj-00':
            print("  [警告] IWENCAI_API_KEY 使用默认占位值，请配置真实的 API Key")
            self._available = False
            return False
        
        self._available = True
        return self._available
    
    def query(self, query: str, page: str = None, limit: str = None) -> Optional[Dict]:
        """
        使用 OpenAPI 执行查询
        
        Args:
            query: 查询字符串
            page: 分页参数
            limit: 每页条数
            
        Returns:
            包含 datas、code_count、chunks_info 等字段的字典，失败返回 None
        """
        if not self._check_available():
            return None
        
        page = page or self.DEFAULT_PAGE
        limit = limit or self.DEFAULT_LIMIT
        
        payload = {
            "query": query,
            "page": page,
            "limit": limit,
            "is_cache": self.DEFAULT_IS_CACHE,
            "expand_index": self.DEFAULT_EXPAND_INDEX
        }
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"  使用问财 OpenAPI 查询: {query}")
            
            resp = requests.post(
                self.DEFAULT_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"  API 响应状态码: {resp.status_code}")
            print(f"  API 响应头: {dict(resp.headers)}")
            
            raw_text = resp.text
            print(f"  API 原始响应内容 (前500字符): {raw_text[:500] if len(raw_text) > 500 else raw_text}")
            
            result = resp.json()
            
            if isinstance(result, dict):
                status_code = result.get("status_code", 0)
                if status_code != 0:
                    status_msg = result.get("status_msg", "未知错误")
                    print(f"  [警告] OpenAPI 返回错误: status_code={status_code}, msg={status_msg}")
                    return None
                
                return {
                    "datas": result.get("datas", []),
                    "code_count": result.get("code_count", 0),
                    "chunks_info": result.get("chunks_info", {}),
                    "status_code": 0
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"  [警告] OpenAPI 请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"  [警告] OpenAPI 响应解析失败: {e}")
            try:
                print(f"  无法解析的响应内容: {resp.text[:1000] if 'resp' in dir() else '无法获取响应'}")
            except Exception:
                pass
            return None
        except Exception as e:
            print(f"  [警告] OpenAPI 查询异常: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查 OpenAPI 是否完全可用"""
        return self._check_available()


class WencaiFetcher:
    """
    问财人气排名采集器
    
    仅使用 OpenAPI 方式进行数据查询
    旧 URL 方式已移除
    """
    
    def __init__(self):
        self._openapi = WencaiOpenAPI()
    
    def fetch(self, top: int = 50) -> List[StockRank]:
        """获取问财人气排名
        
        Args:
            top: 获取前N名
            
        Returns:
            股票排名列表
        """
        print("【问财】正在采集...")
        
        if not self._openapi.is_available():
            print("  采集失败: OpenAPI 不可用")
            return []
        
        try:
            result = self._openapi.query(f"人气排名前{top}", limit=str(top))
            
            if not result:
                print("  采集失败: 查询无结果")
                return []
            
            ranks = self._parse_result(result, top)
            
            if ranks:
                print(f"  成功获取 {len(ranks)} 只股票")
            else:
                print("  采集失败: 未解析到数据")
            
            return ranks
            
        except Exception as e:
            print(f"  采集失败: {e}")
            return []
    
    def _parse_result(self, result: Dict, top: int) -> List[StockRank]:
        """解析 OpenAPI 返回结果
        
        OpenAPI 返回格式：
        {
            "datas": [...],
            "code_count": N,
            "chunks_info": {},
            "status_code": 0
        }
        """
        ranks = []
        
        datas = result.get('datas', [])
        if not datas:
            return ranks
        
        for i, item in enumerate(datas[:top]):
            code = item.get('股票代码', item.get('code', item.get('stockCode', '')))
            name = item.get('股票简称', item.get('name', item.get('stockName', '')))
            
            if code and name:
                code_str = str(code)
                if '.' in code_str:
                    code_str = code_str.split('.')[0]
                
                ranks.append(StockRank(
                    code=code_str,
                    name=str(name),
                    rank=i + 1,
                    heat_score=top - i,
                    source='wencai'
                ))
        
        return ranks


class XueqiuFetcher:
    """雪球热榜采集器"""

    def __init__(self):
        self.session = requests.Session()

    def fetch(self) -> List[StockRank]:
        """获取雪球热榜A股前50"""
        html = self._fetch_page()
        ranks = self._parse_html(html)
        if not ranks:
            raise Exception("未能从页面解析到股票数据")
        return ranks

    def _fetch_page(self) -> str:
        """获取页面HTML"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        resp = self.session.get('https://xueqiu.com/hot/stock', headers=headers, timeout=15)
        return resp.text

    def _parse_html(self, html: str) -> List[StockRank]:
        """解析HTML获取股票数据"""
        ranks = []
        pattern = re.compile(r'"name":"([^"]+)","value":[^}]*"symbol":"(SH|SZ)(\d+)"')
        seen = set()

        for match in pattern.finditer(html):
            name, market, code = match.groups()
            full_code = market + code
            if full_code in seen or len(ranks) >= 50:
                continue
            seen.add(full_code)

            ranks.append(StockRank(
                code=code,
                name=name,
                rank=len(ranks) + 1,
                heat_score=100 - len(ranks),
                source='xueqiu'
            ))

        return ranks


class EastmoneyFetcher:
    """东方财富人气排名采集器"""

    def __init__(self):
        self.session = requests.Session()

    def fetch(self) -> List[StockRank]:
        """获取东方财富人气排名前50"""
        return self._get_rank_data()

    def _get_rank_data(self) -> List[StockRank]:
        """获取排名数据"""
        url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
        payload = {
            "appId": "stockrank",
            "globalId": "786e4c21-70dc-435a-93bb-38",
            "marketType": "",
            "rankType": "1",
            "pageNo": 1,
            "pageSize": 100,
            "fromDate": "",
            "toDate": "",
            "stockIndustry": "",
            "stockCode": "",
            "stockName": "",
            "clientSource": "web",
            "clientVersion": "1.0.0",
        }
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://vipmoney.eastmoney.com',
            'Referer': 'https://vipmoney.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        resp = self.session.post(url, json=payload, headers=headers, timeout=15)
        data = resp.json()

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> List[StockRank]:
        """解析响应数据"""
        if data.get('status', -1) != 0:
            raise Exception(f"API返回错误: status={data.get('status')}")

        ranks = []
        for item in data.get('data', [])[:50]:
            sc = item.get('sc', '')
            if len(sc) < 8:
                continue
            code = sc[2:]

            ranks.append(StockRank(
                code=code,
                name='',
                rank=item.get('rk', len(ranks) + 1),
                heat_score=100 - len(ranks),
                source='eastmoney'
            ))

        return ranks


def normalize_code(code: str) -> str:
    """标准化股票代码"""
    if len(code) == 6:
        return validate_a_stock_code(code)
    if len(code) == 8 and code[:2] in ('SH', 'SZ'):
        return validate_a_stock_code(code[2:])
    if len(code) == 9 and code[6:] in ('.SH', '.SZ'):
        return validate_a_stock_code(code[:6])
    return ''


def validate_a_stock_code(code: str) -> str:
    """验证A股代码"""
    if len(code) != 6 or not code.isdigit():
        return ''
    first = code[0]
    if first not in ('6', '0', '3', '8', '4'):
        return ''
    return code


def calculate_composite(wencai: List[StockRank], xueqiu: List[StockRank], eastmoney: List[StockRank]) -> List[CompositeRank]:
    """计算复合热度"""
    stock_map: Dict[str, CompositeRank] = {}

    for r in wencai:
        code = normalize_code(r.code)
        if not code:
            continue
        if code not in stock_map:
            stock_map[code] = CompositeRank(code=code, name=r.name)
        stock_map[code].wencai_rank = r.rank
        stock_map[code].appear_count += 1

    for r in xueqiu:
        code = normalize_code(r.code)
        if not code:
            continue
        if code not in stock_map:
            stock_map[code] = CompositeRank(code=code, name=r.name)
        stock_map[code].xueqiu_rank = r.rank
        stock_map[code].appear_count += 1

    for r in eastmoney:
        code = normalize_code(r.code)
        if not code:
            continue
        if code not in stock_map:
            stock_map[code] = CompositeRank(code=code, name=r.name)
        if not stock_map[code].name and r.name:
            stock_map[code].name = r.name
        stock_map[code].eastmoney_rank = r.rank
        stock_map[code].appear_count += 1

    for stock in stock_map.values():
        score = 0.0
        if stock.wencai_rank > 0:
            score += 100 - stock.wencai_rank
        if stock.xueqiu_rank > 0:
            score += 100 - stock.xueqiu_rank
        if stock.eastmoney_rank > 0:
            score += 100 - stock.eastmoney_rank

        if stock.appear_count == 2:
            score += 20
        elif stock.appear_count == 3:
            score += 50

        stock.composite_score = score / 3.5

    return sorted(stock_map.values(), key=lambda x: x.composite_score, reverse=True)


def print_table(ranks: List[CompositeRank], top: int):
    """打印表格"""
    print()
    print("┌──────┬──────────┬────────────┬──────┬──────┬──────┬──────────┬──────┐")
    print("│ 排名 │   代码   │    名称    │ 问财 │ 雪球 │ 东财 │  热度分  │ 出现 │")
    print("├──────┼──────────┼────────────┼──────┼──────┼──────┼──────────┼──────┤")

    for i, r in enumerate(ranks[:top]):
        wc = str(r.wencai_rank) if r.wencai_rank > 0 else "-"
        xq = str(r.xueqiu_rank) if r.xueqiu_rank > 0 else "-"
        em = str(r.eastmoney_rank) if r.eastmoney_rank > 0 else "-"

        print(f"│ {i+1:4d} │ {r.code:8s} │ {r.name:10s} │ {wc:>4s} │ {xq:>4s} │ {em:>4s} │ {r.composite_score:8.1f} │ {r.appear_count:4d} │")

    print("└──────┴──────────┴────────────┴──────┴──────┴──────┴──────────┴──────┘")
    print()


def print_json(ranks: List[CompositeRank], top: int):
    """打印JSON"""
    result = []
    for i, r in enumerate(ranks[:top]):
        result.append({
            "rank": i + 1,
            "code": r.code,
            "name": r.name,
            "wencai_rank": r.wencai_rank if r.wencai_rank > 0 else None,
            "xueqiu_rank": r.xueqiu_rank if r.xueqiu_rank > 0 else None,
            "eastmoney_rank": r.eastmoney_rank if r.eastmoney_rank > 0 else None,
            "composite_score": round(r.composite_score, 1),
            "appear_count": r.appear_count,
        })
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='股票热度排名采集器 - Python版')
    parser.add_argument('--top', type=int, default=50, help='获取前N名 (默认: 50)')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='输出格式 (默认: table)')
    args = parser.parse_args()

    print("=== 股票热度排名采集器 ===")
    print(f"采集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 检查问财 API Key 是否配置
    if not check_api_key_configured():
        print("=" * 60)
        print("⚠️  警告：问财 API Key 未配置")
        print("=" * 60)
        print(get_api_key_reminder())
        print("问财人气排名功能将无法使用")
        print("将只使用雪球和东方财富的数据进行计算")
        print("=" * 60 + "\n")

    # 采集问财数据
    wencai_ranks = []
    wencai_fetcher = WencaiFetcher()
    try:
        wencai_ranks = wencai_fetcher.fetch(50)
        if wencai_ranks:
            print(f"【问财】成功获取 {len(wencai_ranks)} 只股票")
    except Exception as e:
        print(f"【问财】采集失败: {e}")

    # 采集雪球数据
    print("\n【雪球】正在采集...")
    xueqiu_ranks = []
    try:
        fetcher = XueqiuFetcher()
        xueqiu_ranks = fetcher.fetch()
        print(f"  成功获取 {len(xueqiu_ranks)} 只A股")
    except Exception as e:
        print(f"  采集失败: {e}")

    # 采集东财数据
    print("\n【东财】正在采集...")
    eastmoney_ranks = []
    try:
        fetcher = EastmoneyFetcher()
        eastmoney_ranks = fetcher.fetch()
        print(f"  成功获取 {len(eastmoney_ranks)} 只股票")
    except Exception as e:
        print(f"  采集失败: {e}")

    # 计算复合热度
    print("\n=== 复合热度排名 ===")
    print(f"问财: {len(wencai_ranks)} | 雪球: {len(xueqiu_ranks)} | 东财: {len(eastmoney_ranks)}")

    result = calculate_composite(wencai_ranks, xueqiu_ranks, eastmoney_ranks)

    if args.format == 'json':
        print_json(result, args.top)
    else:
        print_table(result, args.top)


if __name__ == '__main__':
    main()
