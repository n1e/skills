#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复盘报告数据模型
"""

from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .market import MarketData, VolumeData
    from .stock import SurgeStock, CompositeHeatRank


def _market_factory():
    from .market import MarketData
    return MarketData()


@dataclass
class DailyReview:
    """每日复盘报告"""
    date: str = ""
    market: 'MarketData' = field(default_factory=_market_factory)
    volume_history: List['VolumeData'] = field(default_factory=list)
    surge_stocks: List['SurgeStock'] = field(default_factory=list)
    heat_ranks: List['CompositeHeatRank'] = field(default_factory=list)
