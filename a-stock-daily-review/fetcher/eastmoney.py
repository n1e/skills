#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富人气排名采集器
"""

from typing import List

import requests

from logger import logger
from utils.retry import retry_with_backoff


class EastmoneyFetcher:
    """东方财富人气排名采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://vipmoney.eastmoney.com',
            'Referer': 'https://vipmoney.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    
    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def fetch(self, top: int = 50) -> List[dict]:
        """
        获取东方财富人气排名前50
        
        Args:
            top: 获取前N只股票
            
        Returns:
            人气排名列表
        """
        logger.info(f"获取东财人气排名TOP{top}")
        
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
        
        try:
            resp = self.session.post(url, json=payload, headers=self.headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            ranks = []
            for i, item in enumerate(data.get('data', [])[:top]):
                sc = item.get('sc', '')
                if len(sc) < 8:
                    continue
                code = sc[2:]  # 去掉前缀
                name = item.get('n', '')
                
                ranks.append({
                    'code': code,
                    'name': name,
                    'rank': i + 1,
                    'heat_score': 100 - i,
                    'source': 'eastmoney'
                })
            
            logger.info(f"东财获取到 {len(ranks)} 只股票")
            return ranks
            
        except Exception as e:
            logger.error(f"东财人气排名获取失败: {e}")
            raise