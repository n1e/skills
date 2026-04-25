#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨停原因分析器
分析涨停股票的归类原因
"""

from typing import List


class ReasonAnalyzer:
    """涨停原因分析器"""
    
    # 预定义原因分类关键词
    REASON_CATEGORIES = {
        '业绩预增': ['业绩', '增长', '利润', '预增', '扭亏', '盈利', '年报', '季报'],
        '并购重组': ['重组', '并购', '收购', '借壳', '股权', '转让', '资产注入'],
        '政策利好': ['政策', '补贴', '扶持', '规划', '利好', '新基建', '国家', '部委'],
        '概念炒作': ['概念', '题材', '风口', 'ai', '人工智能', '新能源', '芯片', '元宇宙', '数字经济'],
        '资金推动': ['资金', '主力', '大单', '流入', '抢筹', '机构', '游资'],
        '技术突破': ['突破', '创新高', '新高', '启动', '爆发', '涨停板'],
        '行业景气': ['行业', '景气', '复苏', '供需', '涨价', '周期'],
        '新产品/订单': ['订单', '产品', '签约', '中标', '合同', '发布', '量产'],
        '股权激励': ['激励', '回购', '增持', '员工持股', '股权激励'],
        '高送转预期': ['送转', '分红', '高送', '派息', '转增'],
    }
    
    @classmethod
    def analyze(cls, reason: str) -> str:
        """
        分析涨停原因并分类
        
        Args:
            reason: 原始涨停原因文本
            
        Returns:
            分类后的原因类别
        """
        if not reason:
            return "其他"
        
        reason_lower = reason.lower()
        
        for category, keywords in cls.REASON_CATEGORIES.items():
            if any(kw in reason_lower for kw in keywords):
                return category
        
        return "其他"
    
    @classmethod
    def batch_analyze(cls, reasons: List[str]) -> List[str]:
        """
        批量分析原因
        
        Args:
            reasons: 原因文本列表
            
        Returns:
            分类结果列表
        """
        return [cls.analyze(reason) for reason in reasons]
    
    @classmethod
    def get_category_stats(cls, reasons: List[str]) -> dict:
        """
        统计原因分类分布
        
        Args:
            reasons: 原因文本列表
            
        Returns:
            分类统计字典 {category: count}
        """
        categories = cls.batch_analyze(reasons)
        stats = {}
        
        for cat in categories:
            stats[cat] = stats.get(cat, 0) + 1
        
        return stats