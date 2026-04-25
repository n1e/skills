#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare数据采集器
用于获取市场新闻情绪指标等数据
"""

from typing import Optional
from datetime import datetime

from logger import logger


class AKShareFetcher:
    """AKShare数据采集器"""
    
    def __init__(self):
        self._akshare_available = True
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            self._akshare_available = False
            logger.warning("akshare未安装，市场新闻情绪指标将不可用")
    
    def get_news_sentiment(self) -> Optional[dict]:
        """
        获取市场新闻情绪指标
        
        Returns:
            dict: 包含日期和市场情绪指数的字典，失败返回None
            示例: {'date': '2024-10-31', 'sentiment_index': 1.0073}
        """
        if not self._akshare_available:
            logger.warning("akshare不可用，无法获取市场新闻情绪指标")
            return None
        
        try:
            df = self.ak.index_news_sentiment_scope()
            if df is not None and len(df) > 0:
                # 获取最新一条记录
                latest = df.iloc[-1]
                date_str = str(latest.get('日期', ''))
                sentiment = float(latest.get('市场情绪指数', 1.0))
                
                result = {
                    'date': date_str,
                    'sentiment_index': sentiment
                }
                logger.info(f"市场新闻情绪指标: {sentiment:.4f} (日期: {date_str})")
                return result
            else:
                logger.warning("市场新闻情绪数据为空")
                return None
        except Exception as e:
            logger.error(f"获取市场新闻情绪指标失败: {e}")
            return None
    
    def get_news_sentiment_history(self, days: int = 30) -> list:
        """
        获取市场新闻情绪历史数据
        
        Args:
            days: 获取天数
            
        Returns:
            list: 情绪历史数据列表
        """
        if not self._akshare_available:
            logger.warning("akshare不可用，无法获取市场新闻情绪历史")
            return []
        
        try:
            df = self.ak.index_news_sentiment_scope()
            if df is not None and len(df) > 0:
                # 获取最近N条记录
                recent = df.tail(days)
                results = []
                for _, row in recent.iterrows():
                    date_str = str(row.get('日期', ''))
                    sentiment = float(row.get('市场情绪指数', 1.0))
                    results.append({
                        'date': date_str,
                        'sentiment_index': sentiment
                    })
                logger.info(f"获取到 {len(results)} 条市场新闻情绪历史数据")
                return results
            else:
                logger.warning("市场新闻情绪历史数据为空")
                return []
        except Exception as e:
            logger.error(f"获取市场新闻情绪历史失败: {e}")
            return []