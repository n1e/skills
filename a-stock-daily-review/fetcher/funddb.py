#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FundDB恐惧贪婪指数采集器
数据来源: 乐股网站 (legulegu.com)
通过市场活跃度数据计算恐惧贪婪指数
"""

import requests
import re
from datetime import datetime
from typing import List, Optional

from logger import logger


class FearGreedData:
    """恐惧贪婪指数数据"""
    def __init__(self):
        self.date: str = ""
        self.fear_index: float = 0.0  # 恐惧指数 (0-100)
        self.index_value: float = 0.0  # 指数点位


class FunddbFetcher:
    """FundDB恐惧贪婪指数采集器"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session = None
    
    def _get_session(self):
        """获取HTTP会话"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            })
        return self._session
    
    def fetch_fear_greed(self, symbol: str = "上证指数", days: int = 30) -> List[FearGreedData]:
        """
        获取恐惧贪婪指数数据
        
        Args:
            symbol: 指数代码，"上证指数" 或 "沪深300"
            days: 获取天数
            
        Returns:
            恐惧贪婪指数数据列表
        """
        # 尝试使用akshare（如果可用）
        try:
            import akshare as ak
            if hasattr(ak, 'index_fear_greed_funddb'):
                return self._fetch_via_akshare(symbol, days)
        except Exception:
            pass
        
        # 回退到乐股数据计算
        return self._fetch_via_legu(symbol, days)
    
    def _fetch_via_akshare(self, symbol: str, days: int) -> List[FearGreedData]:
        """通过akshare获取数据"""
        import akshare as ak
        
        symbol_map = {
            "上证指数": "上证指数",
            "沪深300": "沪深300",
        }
        
        ak_symbol = symbol_map.get(symbol, "上证指数")
        df = ak.index_fear_greed_funddb(symbol=ak_symbol)
        
        results = []
        for _, row in df.tail(days).iterrows():
            data = FearGreedData()
            data.date = str(row.get('date', ''))
            data.fear_index = float(row.get('fear', 0))
            data.index_value = float(row.get('index', 0))
            results.append(data)
        
        logger.info(f"akshare获取恐惧贪婪指数成功: {len(results)}条记录")
        return results
    
    def _fetch_via_legu(self, symbol: str, days: int) -> List[FearGreedData]:
        """通过乐股数据计算恐惧贪婪指数"""
        url = 'https://legulegu.com/stockdata/market-activity'
        
        try:
            session = self._get_session()
            resp = session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            
            # 从HTML中提取数据
            chart_matches = re.findall(r'id="([^"]+)"[^>]*data-chart=\'(\d+)\'', resp.text)
            data = {}
            for name, val in chart_matches:
                data[name] = int(val)
            
            # 计算恐惧贪婪指数
            # 基于上涨家数占比计算
            total_up = data.get('totalUp', 0)
            total_down = data.get('totalDown', 0)
            total = data.get('total', 0)
            
            if total > 0:
                # 上涨占比作为贪婪指数 (0-100)
                greed_index = (total_up / total) * 100
            else:
                greed_index = 50
            
            # 恐惧指数 = 100 - 贪婪指数
            fear_index = 100 - greed_index
            
            # 创建单条记录
            result = FearGreedData()
            result.date = datetime.now().strftime('%Y-%m-%d')
            result.fear_index = round(fear_index, 2)
            result.index_value = data.get('total', 0)
            
            logger.info(f"乐股计算恐惧贪婪指数: 恐惧={fear_index:.1f}, 贪婪={greed_index:.1f}")
            return [result]
            
        except Exception as e:
            logger.error(f"乐股获取恐惧贪婪指数失败: {e}")
            return []
    
    def get_latest_fear_greed(self, symbol: str = "上证指数") -> Optional[FearGreedData]:
        """获取最新的恐惧贪婪指数"""
        data_list = self.fetch_fear_greed(symbol, days=1)
        if data_list:
            return data_list[-1]
        return None