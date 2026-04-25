#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球热榜采集器
"""

import re
import time
from typing import List

import requests

from logger import logger
from utils.retry import retry_with_backoff


class XueqiuFetcher:
    """雪球热榜采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    
    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def fetch(self, top: int = 50) -> List[dict]:
        """
        获取雪球热榜A股前50
        
        Args:
            top: 获取前N只股票
            
        Returns:
            人气排名列表
        """
        logger.info(f"获取雪球热榜TOP{top}")
        
        url = 'https://xueqiu.com/hot/stock'
        
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            html = resp.text
            
            ranks = []
            pattern = re.compile(r'"name":"([^"]+)","value":[^}]*"symbol":"(SH|SZ)(\d+)"')
            seen = set()
            
            for match in pattern.finditer(html):
                name, market, code = match.groups()
                full_code = market + code
                if full_code in seen or len(ranks) >= top:
                    continue
                seen.add(full_code)
                
                # 解码雪球返回的UTF-8字节序列（被错误解释为Latin-1）
                # 例如: "Ã¤Â¸Â­Ã¥ÂÂ½Ã©ÂÂÃ¤Â¸Â" -> "中国铝业"
                try:
                    decoded_name = name.encode('latin-1').decode('utf-8')
                except:
                    try:
                        decoded_name = name.encode('utf-8').decode('unicode_escape')
                    except:
                        decoded_name = name
                
                ranks.append({
                    'code': code,
                    'name': decoded_name,
                    'rank': len(ranks) + 1,
                    'heat_score': 100 - len(ranks),
                    'source': 'xueqiu'
                })
            
            logger.info(f"雪球获取到 {len(ranks)} 只A股")
            return ranks
            
        except Exception as e:
            logger.error(f"雪球热榜获取失败: {e}")
            raise