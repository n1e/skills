#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热度排名分析器
综合多个数据源计算股票热度排名
"""

from typing import List, Dict

from models.stock import HeatRank, CompositeHeatRank
from logger import logger


def _to_rank(r) -> HeatRank:
    """确保 r 是 HeatRank 对象（兼容 dict 和 HeatRank）"""
    if isinstance(r, HeatRank):
        return r
    return HeatRank(
        code=r.get('code', ''),
        name=r.get('name', ''),
        rank=r.get('rank', 0),
        heat_score=r.get('heat_score', 0),
        source=r.get('source', ''),
    )


class HeatRanker:
    """热度排名分析器"""
    
    @staticmethod
    def calculate_composite_heat(
        wencai_ranks,
        xueqiu_ranks,
        eastmoney_ranks,
        top: int = 50,
    ) -> List[CompositeHeatRank]:
        """
        计算复合热度排名

        Args:
            wencai_ranks: 问财人气排名列表（问财即同花顺数据）
            xueqiu_ranks: 雪球热榜列表
            eastmoney_ranks: 东财人气排名列表
            top: 返回前N名

        Returns:
            复合热度排名列表
        """
        logger.info("开始计算复合热度排名")

        # 使用字典聚合数据
        stock_map: Dict[str, CompositeHeatRank] = {}

        # 处理问财数据（问财=同花顺数据，只需一份）
        for r in wencai_ranks:
            rank = _to_rank(r)
            if len(rank.code) != 6:
                continue
            if rank.code not in stock_map:
                stock_map[rank.code] = CompositeHeatRank(code=rank.code, name=rank.name)
            stock_map[rank.code].wencai_rank = rank.rank
            stock_map[rank.code].appear_count += 1

        # 处理雪球数据
        for r in xueqiu_ranks:
            rank = _to_rank(r)
            if len(rank.code) != 6:
                continue
            if rank.code not in stock_map:
                stock_map[rank.code] = CompositeHeatRank(code=rank.code, name=rank.name)
            stock_map[rank.code].xueqiu_rank = rank.rank
            stock_map[rank.code].appear_count += 1

        # 处理东财数据
        for r in eastmoney_ranks:
            rank = _to_rank(r)
            if len(rank.code) != 6:
                continue
            if rank.code not in stock_map:
                stock_map[rank.code] = CompositeHeatRank(code=rank.code, name=rank.name)
            if not stock_map[rank.code].name and rank.name:
                stock_map[rank.code].name = rank.name
            stock_map[rank.code].eastmoney_rank = rank.rank
            stock_map[rank.code].appear_count += 1

        # 计算复合得分（三平台：问财+雪球+东财）
        total_sources = 3.5

        for stock in stock_map.values():
            score = 0.0
            if stock.wencai_rank > 0:
                score += 100 - stock.wencai_rank
            if stock.xueqiu_rank > 0:
                score += 100 - stock.xueqiu_rank
            if stock.eastmoney_rank > 0:
                score += 100 - stock.eastmoney_rank

            # 出现次数越多，得分越高（体现多平台关注）
            if stock.appear_count == 2:
                score += 20
            elif stock.appear_count == 3:
                score += 50

            stock.composite_score = score / total_sources

        # 排序并返回前top名
        sorted_ranks = sorted(stock_map.values(), key=lambda x: x.composite_score, reverse=True)[:top]

        logger.info(f"复合热度排名计算完成，共{len(sorted_ranks)}只股票")
        return sorted_ranks
    
    @staticmethod
    def calculate_availability_rate(
        wencai_ranks,
        xueqiu_ranks,
        eastmoney_ranks,
    ) -> Dict[str, float]:
        """
        计算各数据源可用率

        Returns:
            各数据源可用率字典
        """
        rates = {}

        rates['wencai'] = len(wencai_ranks) / 50.0 if wencai_ranks else 0.0
        rates['xueqiu'] = len(xueqiu_ranks) / 50.0 if xueqiu_ranks else 0.0
        rates['eastmoney'] = len(eastmoney_ranks) / 50.0 if eastmoney_ranks else 0.0

        return rates