#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown报告生成器
"""

from datetime import datetime
from typing import List

from models.market import MarketData
from models.stock import SurgeStock, CompositeHeatRank
from reporter.template_renderer import TemplateRenderer
from analyzer.reason_analyzer import ReasonAnalyzer


class MarkdownGenerator:
    """Markdown报告生成器"""
    
    def __init__(self, review_data):
        """
        初始化生成器
        
        Args:
            review_data: DailyReview对象或类似结构的数据
        """
        self.review = review_data
        self.renderer = TemplateRenderer()
    
    def generate(self) -> str:
        """生成完整的Markdown报告"""
        lines = []
        
        # 标题
        lines.append("# A股每日复盘报告")
        lines.append(f"\n**日期**: {self.review.date}\n")
        
        # 大盘概况
        lines.append("## 📊 大盘概况\n")
        lines.append(self.renderer.render_market_summary(self.review.market))
        lines.append("")
        
        # 市场情绪
        lines.append("## 🎭 市场情绪\n")
        lines.append(self.renderer.render_market_sentiment(self.review.market))
        lines.append("")
        
        # 涨跌分布
        dist_table = self.renderer.render_distribution_table(self.review.market)
        if dist_table:
            lines.append("## 📊 涨跌分布\n")
            lines.append(dist_table)
            lines.append("")
        
        # 成交量趋势
        if self.review.volume_history:
            lines.append("## 📈 最近30日成交量\n")
            lines.append(self.renderer.render_volume_history(self.review.volume_history))
            lines.append("")
        
        # 涨停分析
        if self.review.surge_stocks:
            lines.append(f"## 🚀 涨停分析 ({len(self.review.surge_stocks)}只)\n")
            
            # 确保每只股票都有原因分类
            for stock in self.review.surge_stocks:
                if not stock.reason_category:
                    stock.reason_category = ReasonAnalyzer.analyze(stock.reason)
            
            lines.append(self.renderer.render_surge_analysis(self.review.surge_stocks))
        
        # 人气排名
        if self.review.heat_ranks:
            lines.append(f"## 🔥 人气排名TOP50（综合排名）\n")
            lines.append(self.renderer.render_heat_ranks(self.review.heat_ranks))
            lines.append("")
        
        # 页脚
        lines.append("---\n")
        lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)