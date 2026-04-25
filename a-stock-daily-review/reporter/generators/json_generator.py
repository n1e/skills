#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON报告生成器
"""

import json
from datetime import datetime

from models.market import MarketData
from models.stock import SurgeStock, CompositeHeatRank


class JsonGenerator:
    """JSON报告生成器"""
    
    def __init__(self, review_data):
        """
        初始化生成器
        
        Args:
            review_data: DailyReview对象或类似结构的数据
        """
        self.review = review_data
    
    def generate(self, indent: int = 2) -> str:
        """
        生成JSON格式报告
        
        Args:
            indent: JSON缩进空格数
            
        Returns:
            JSON字符串
        """
        data = {
            "date": self.review.date,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "market": {
                "up_count": self.review.market.up_count,
                "down_count": self.review.market.down_count,
                "flat_count": self.review.market.flat_count,
                "total_count": self.review.market.total_count,
                "rise_fall_ratio": round(self.review.market.rise_fall_ratio, 2),
                "limit_up_count": self.review.market.limit_up_count,
                "limit_down_count": self.review.market.limit_down_count,
                "limit_ratio": round(self.review.market.limit_ratio, 2),
                "total_volume": self.review.market.total_volume,
                "main_inflow": self.review.market.main_inflow,
                "fear_index": round(self.review.market.fear_index, 1),
                "greed_index": round(self.review.market.greed_index, 1),
            },
            "volume_history": [
                {"date": v.date, "volume": v.volume}
                for v in self.review.volume_history
            ],
            "surge_stocks": [
                {
                    "code": s.code,
                    "name": s.name,
                    "change_pct": round(s.change_pct, 1) if s.change_pct else 0,
                    "reason": s.reason or "",
                    "reason_category": s.reason_category or ""
                }
                for s in self.review.surge_stocks
            ],
            "heat_ranks": [
                {
                    "rank": i + 1,
                    "code": r.code,
                    "name": r.name,
                    "wencai_rank": r.wencai_rank if r.wencai_rank > 0 else None,
                    "xueqiu_rank": r.xueqiu_rank if r.xueqiu_rank > 0 else None,
                    "eastmoney_rank": r.eastmoney_rank if r.eastmoney_rank > 0 else None,
                    "thsi_rank": r.thsi_rank if r.thsi_rank > 0 else None,
                    "composite_score": round(r.composite_score, 1),
                    "appear_count": r.appear_count
                }
                for i, r in enumerate(self.review.heat_ranks)
            ]
        }
        
        return json.dumps(data, ensure_ascii=False, indent=indent)