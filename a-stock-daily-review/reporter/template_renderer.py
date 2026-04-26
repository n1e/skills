#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板渲染器
用于生成Markdown格式的复盘报告
"""

from typing import Dict, Any, List
from models.market import VolumeData


class TemplateRenderer:
    """模板渲染器（使用Markdown表格格式化）"""
    
    @staticmethod
    def render_market_summary(market_data) -> str:
        """渲染大盘概况表格（所有指标统一用百分数格式）"""
        lines = []
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 上涨家数 | {market_data.up_count} |")
        lines.append(f"| 下跌家数 | {market_data.down_count} |")
        lines.append(f"| 平盘家数 | {market_data.flat_count} |")
        lines.append(f"| 停牌家数 | {market_data.suspension_count} |")
        lines.append(f"| 涨停家数 | {market_data.limit_up_count} |")
        lines.append(f"| 跌停家数 | {market_data.limit_down_count} |")
        lines.append(f"| 非一字涨停 | {market_data.real_limit_up_count} |")
        lines.append(f"| 非一字跌停 | {market_data.real_limit_down_count} |")
        
        # 计算类指标（统一用百分数格式）
        rise_fall_pct = market_data.rise_fall_ratio * 100
        limit_ratio_pct = market_data.limit_ratio * 100
        real_limit_pct = market_data.real_limit_ratio * 100
        congestion_pct = market_data.congestion
        activity_pct = market_data.market_activity
        
        lines.append(f"| 涨跌比 | {rise_fall_pct:.1f}% |")
        lines.append(f"| 涨跌停比 | {limit_ratio_pct:.1f}% |")
        lines.append(f"| 真实涨跌停比 | {real_limit_pct:.1f}% |")
        lines.append(f"| 大盘拥挤度 | {congestion_pct:.1f}% |")
        lines.append(f"| 市场活跃度 | {activity_pct:.1f}% |")
        
        # 拥挤度说明
        lines.append("")
        lines.append("> **注**: 大盘拥挤度 = 成交额排名前5%的个股成交额占全部A股占比")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_market_sentiment(market_data) -> str:
        """渲染市场情绪指标（表格形式）"""
        lines = []
        lines.append("| 指标 | 数值 | 判断 |")
        lines.append("|------|------|------|")
        lines.append(f"| 恐慌指数 | {market_data.fear_index:.1f}% | {'🔴 恐慌' if market_data.fear_index > 50 else '🟢 正常'} |")
        lines.append(f"| 贪婪指数 | {market_data.greed_index:.1f}% | {'🟢 贪婪' if market_data.greed_index > 50 else '🟡 正常'} |")
        
        # 情绪总结
        if market_data.fear_index > 50:
            sentiment = "🔴 市场恐慌情绪较强"
        elif market_data.greed_index > 50:
            sentiment = "🟢 市场贪婪情绪较强"
        else:
            sentiment = "🟡 市场情绪中性"
        
        lines.append(f"| **情绪判断** | - | **{sentiment}** |")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_distribution_table(market_data) -> str:
        """渲染涨跌分布表格"""
        if market_data.up_0_3 == 0 and market_data.up_3_5 == 0 and market_data.down_0_3 == 0:
            return ""
        
        lines = []
        lines.append("| 区间 | 上涨家数 | 下跌家数 |")
        lines.append("|------|---------|---------|")
        lines.append(f"| -20%~-10% | - | {market_data.down_10_20} |")
        lines.append(f"| -10%~-7% | - | {market_data.down_7_10} |")
        lines.append(f"| -7%~-5% | - | {market_data.down_5_7} |")
        lines.append(f"| -5%~-3% | - | {market_data.down_3_5} |")
        lines.append(f"| -3%~0% | - | {market_data.down_0_3} |")
        lines.append(f"| 0%~3% | {market_data.up_0_3} | - |")
        lines.append(f"| 3%~5% | {market_data.up_3_5} | - |")
        lines.append(f"| 5%~7% | {market_data.up_5_7} | - |")
        lines.append(f"| 7%~10% | {market_data.up_7_10} | - |")
        lines.append(f"| 10%~20% | {market_data.up_10_20} | - |")
        lines.append(f"| **合计** | **{market_data.up_count}** | **{market_data.down_count}** |")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_volume_history(volume_history: List[VolumeData], max_days: int = 30) -> str:
        """渲染成交量历史（表格形式，包含变化率，默认最近30天）"""
        if not volume_history:
            return ""
        
        # 取最近N天数据
        data = volume_history[-max_days:]
        
        lines = []
        lines.append("| 日期 | 成交额(元) | 成交额(亿元) | 较上一日变化 |")
        lines.append("|------|-----------|-------------|-------------|")
        
        prev_volume = None
        for v in data:
            vol_yi = v.volume / 100000000  # 转换为亿元
            
            if prev_volume is not None and prev_volume > 0:
                change_pct = (v.volume - prev_volume) / prev_volume * 100
                if change_pct >= 0:
                    change_str = f"+{change_pct:.1f}%"
                else:
                    change_str = f"{change_pct:.1f}%"
            else:
                change_str = "-"
            
            lines.append(f"| {v.date} | {v.volume:,.0f} | {vol_yi:.0f}亿 | {change_str} |")
            prev_volume = v.volume
        
        # 最后一天高亮
        if data:
            last = data[-1]
            last_yi = last.volume / 100000000
            lines.append("")
            lines.append(f"> **最新成交额**: {last.date} - {last_yi:.0f}亿元")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_heat_ranks(heat_ranks) -> str:
        """渲染人气排名表格"""
        if not heat_ranks:
            return ""
        
        lines = []
        lines.append("| 排名 | 代码 | 名称 | 问财排名 | 雪球排名 | 东财排名 | 热度分 |")
        lines.append("|------|------|------|---------|---------|---------|--------|")
        
        for i, r in enumerate(heat_ranks[:50]):
            wc = str(r.wencai_rank) if r.wencai_rank > 0 else "-"
            xq = str(r.xueqiu_rank) if r.xueqiu_rank > 0 else "-"
            em = str(r.eastmoney_rank) if r.eastmoney_rank > 0 else "-"
            name = r.name if r.name else r.code  # 如果名称缺失，使用代码
            lines.append(f"| {i+1} | {r.code} | {name} | {wc:>4s} | {xq:>4s} | {em:>4s} | {r.composite_score:8.1f} |")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_news_ranks(news_ranks) -> str:
        """渲染新闻资讯热度排名表格"""
        if not news_ranks:
            return ""
        
        lines = []
        lines.append("| 排名 | 资讯标题 | 来源数 | 来源平台 | 热度分 |")
        lines.append("|------|---------|--------|---------|--------|")
        
        for i, r in enumerate(news_ranks[:30]):
            title = r.title[:40] + "..." if len(r.title) > 40 else r.title
            sources = ', '.join(r.sources) if r.sources else ''
            sources = sources[:20] + "..." if len(sources) > 20 else sources
            lines.append(f"| {i+1} | {title} | {r.source_count} | {sources} | {r.composite_score:8.1f} |")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_surge_analysis(surge_stocks) -> str:
        """渲染涨停分析"""
        if not surge_stocks:
            return ""
        
        lines = []
        
        # 统计分类
        category_count = {}
        for stock in surge_stocks:
            cat = stock.reason_category if stock.reason_category else "其他"
            category_count[cat] = category_count.get(cat, 0) + 1
        
        # 涨停原因分布表格
        lines.append("### 涨停原因分布\n")
        lines.append("| 概念标签 | 出现次数 |")
        lines.append("|---------|---------|")
        for cat, count in sorted(category_count.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | {count}只 |")
        lines.append("")
        
        # 股票列表表格
        lines.append(f"### 涨停股票列表（全部{len(surge_stocks)}只）\n")
        lines.append("| 代码 | 名称 | 涨幅 | 涨停原因 |")
        lines.append("|------|------|------|----------|")
        
        # 按涨幅排序
        sorted_stocks = sorted(surge_stocks, key=lambda x: x.change_pct, reverse=True)
        for stock in sorted_stocks[:100]:
            reason = stock.reason[:30] + "..." if len(stock.reason) > 30 else stock.reason
            lines.append(f"| {stock.code} | {stock.name} | {stock.change_pct:.1f}% | {reason} |")
        
        lines.append("")
        return "\n".join(lines)