#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票相关数据模型
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SurgeStock:
    """涨停/涨停板股票"""
    code: str = ""
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    reason: str = ""
    reason_category: str = ""


@dataclass
class HeatRank:
    """人气排名"""
    code: str = ""
    name: str = ""
    rank: int = 0
    heat_score: int = 0
    source: str = ""  # 'wencai', 'xueqiu', 'eastmoney', 'thsi'


@dataclass
class CompositeHeatRank:
    """复合人气排名"""
    code: str = ""
    name: str = ""
    wencai_rank: int = 0
    xueqiu_rank: int = 0
    eastmoney_rank: int = 0
    thsi_rank: int = 0
    composite_score: float = 0.0
    appear_count: int = 0
