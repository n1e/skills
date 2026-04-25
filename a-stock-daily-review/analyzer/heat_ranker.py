#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热度排名分析器
综合多个数据源计算股票热度排名
"""

from typing import List, Dict

from models.stock import HeatRank, CompositeHeatRank
from logger import logger


class HeatRanker:
    """热度排名分析器"""
    
    @staticmethod
    def calculate_composite_heat(
        thsi_ranks: List[Dict],
        xueqiu_ranks: List[Dict],
        eastmoney_ranks: List[Dict],
        top: int = 50,
        wencai_ranks: List[Dict] = None  # 兼容旧参数名
    ) -> List[CompositeHeatRank]:
        """
        计算复合热度排名
        
        Args:
            thsi_ranks: 同花顺人气排名列表
            xueqiu_ranks: 雪球热榜列表
            eastmoney_ranks: 东财人气排名列表
            top: 返回前N名
            
        Returns:
            复合热度排名列表
        """
        logger.info("开始计算复合热度排名")
        
        # 使用字典聚合数据
        stock_map: Dict[str, CompositeHeatRank] = {}
        
        # 处理同花顺数据
        for r in thsi_ranks:
            code = r.get('code', '')
            if len(code) != 6:
                continue
            
            if code not in stock_map:
                stock_map[code] = CompositeHeatRank(code=code, name=r.get('name', ''))
            stock_map[code].wencai_rank = r.get('rank', 0)  # 保持字段名兼容
            stock_map[code].appear_count += 1
        
        # 处理雪球数据
        for r in xueqiu_ranks:
            code = r.get('code', '')
            if len(code) != 6:
                continue
            
            if code not in stock_map:
                stock_map[code] = CompositeHeatRank(code=code, name=r.get('name', ''))
            stock_map[code].xueqiu_rank = r.get('rank', 0)
            stock_map[code].appear_count += 1
        
        # 处理东财数据
        for r in eastmoney_ranks:
            code = r.get('code', '')
            if len(code) != 6:
                continue
            
            if code not in stock_map:
                stock_map[code] = CompositeHeatRank(code=code, name=r.get('name', ''))
            if not stock_map[code].name and r.get('name'):
                stock_map[code].name = r.get('name')
            stock_map[code].eastmoney_rank = r.get('rank', 0)
            stock_map[code].appear_count += 1
        
        # 计算复合得分（三平台：同花顺+雪球+东财）
        total_sources = 3.5
        
        for stock in stock_map.values():
            score = 0.0
            if stock.wencai_rank > 0:  # 同花顺排名
                score += 100 - stock.wencai_rank
            if stock.xueqiu_rank > 0:
                score += 100 - stock.xueqiu_rank
            if stock.eastmoney_rank > 0:
                score += 100 - stock.eastmoney_rank
            
            # 出现次数越多，得分越高（体现多平台关注）
            if stock.appear_count == 2:
                score += 20
            elif stock.appear_count == 3:
                score += 50  # 三平台共同关注的股票
            
            # 标准化到合理范围
            stock.composite_score = score / total_sources
        
        # 排序并返回前top名
        sorted_ranks = sorted(stock_map.values(), key=lambda x: x.composite_score, reverse=True)[:top]
        
        logger.info(f"复合热度排名计算完成，共{len(sorted_ranks)}只股票")
        return sorted_ranks
    
    @staticmethod
    def calculate_availability_rate(
        wencai_ranks: List[Dict],
        xueqiu_ranks: List[Dict],
        eastmoney_ranks: List[Dict]
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