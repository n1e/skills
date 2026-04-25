#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据模型
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketData:
    """大盘数据"""
    date: str = ""
    up_count: int = 0          # 上涨家数
    down_count: int = 0       # 下跌家数
    flat_count: int = 0       # 平盘家数
    total_count: int = 0      # 总家数
    limit_up_count: int = 0   # 涨停家数（总计）
    limit_down_count: int = 0 # 跌停家数（总计）
    suspension_count: int = 0 # 停牌家数
    real_limit_up_count: int = 0   # 真实涨停（非一字板）
    real_limit_down_count: int = 0 # 真实跌停（非一字板）
    total_volume: float = 0   # 总成交量(手)
    main_inflow: float = 0    # 主力净流入(万)
    _congestion: float = -1.0  # 大盘拥挤度（从乐股获取，-1表示未获取）
    _fear_index: float = -1.0  # 恐慌指数（从funddb获取，-1表示未获取）
    _greed_index: float = -1.0 # 贪婪指数（从funddb获取，-1表示未获取）
    news_sentiment_index: float = -1.0  # 市场新闻情绪指标（从akshare获取，-1表示未获取）
    
    # 涨跌分布 (从乐股 og:description 提取)
    up_0_3: int = 0      # 上涨 0%~3%
    up_3_5: int = 0      # 上涨 3%~5%
    up_5_7: int = 0      # 上涨 5%~7%
    up_7_10: int = 0     # 上涨 7%~10%
    up_10_20: int = 0    # 上涨 10%~20%
    down_0_3: int = 0    # 下跌 0%~3%
    down_3_5: int = 0    # 下跌 3%~5%
    down_5_7: int = 0    # 下跌 5%~7%
    down_7_10: int = 0   # 下跌 7%~10%
    down_10_20: int = 0  # 下跌 10%~20%
    
    # 计算属性
    @property
    def rise_fall_ratio(self) -> float:
        """涨跌比 = 上涨/下跌"""
        if self.down_count == 0:
            return float(self.up_count)
        return self.up_count / self.down_count
    
    @property
    def limit_ratio(self) -> float:
        """涨跌停比 = 涨停/跌停"""
        if self.limit_down_count == 0:
            return float(self.limit_up_count)
        return self.limit_up_count / self.limit_down_count
    
    @property
    def fear_index(self) -> float:
        """恐慌指数 = 跌停/(涨停+跌停) * 100%"""
        # 优先使用从funddb获取的恐惧指数
        if self._fear_index >= 0:
            return self._fear_index
        # 回退到计算值
        total = self.limit_up_count + self.limit_down_count
        if total == 0:
            return 0.0
        return self.limit_down_count / total * 100.0
    
    @fear_index.setter
    def fear_index(self, value: float):
        """设置恐慌指数"""
        self._fear_index = value
    
    @property
    def greed_index(self) -> float:
        """贪心指数 = 涨停/(涨停+跌停) * 100%"""
        # 优先使用从funddb获取的贪婪指数
        if self._greed_index >= 0:
            return self._greed_index
        # 回退到计算值
        total = self.limit_up_count + self.limit_down_count
        if total == 0:
            return 0.0
        return self.limit_up_count / total * 100.0
    
    @greed_index.setter
    def greed_index(self, value: float):
        """设置贪婪指数"""
        self._greed_index = value
    
    @property
    def congestion(self) -> float:
        """
        大盘拥挤度
        优先使用从乐股获取的拥挤度数据，如果没有则计算
        """
        if self._congestion >= 0:
            return self._congestion
        # 回退到计算值
        total_limit = self.limit_up_count + self.limit_down_count
        if total_limit == 0:
            return 0.0
        real_total = self.real_limit_up_count + self.real_limit_down_count
        return real_total / total_limit * 100.0
    
    @property
    def market_activity(self) -> float:
        """
        市场活跃度 = (涨停+跌停) / 总家数 * 100%
        反映市场交投活跃程度
        """
        if self.total_count == 0:
            return 0.0
        return (self.limit_up_count + self.limit_down_count) / self.total_count * 100.0
    
    @property
    def real_limit_ratio(self) -> float:
        """真实涨跌停比 = 真实涨停（非一字板）/ 真实跌停（非一字板）"""
        if self.real_limit_down_count == 0:
            return float(self.real_limit_up_count)
        return self.real_limit_up_count / self.real_limit_down_count


@dataclass
class VolumeData:
    """成交量数据"""
    date: str
    volume: float  # 元（成交额）