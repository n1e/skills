#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML报告生成器
生成包含交互式图表和动画的HTML格式复盘报告
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter

from logger import logger
from models.market import MarketData, VolumeData
from models.stock import SurgeStock
from models.review import DailyReview


class HTMLGenerator:
    """HTML报告生成器"""
    
    def __init__(self, review: DailyReview):
        self.review = review
        self.market = review.market
        self.volume_history = review.volume_history
        self.surge_stocks = review.surge_stocks
        self.heat_ranks = review.heat_ranks
        self.news_ranks = review.news_ranks
    
    def generate(self) -> str:
        """生成完整的HTML报告"""
        return self._build_html()
    
    def _get_weekday(self, date_str: str) -> str:
        """获取星期几"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            return weekdays[date.weekday()]
        except:
            return ''
    
    def _format_date(self, date_str: str) -> str:
        """格式化日期显示"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            return f"{date.year}年{date.month}月{date.day}日"
        except:
            return date_str
    
    def _build_html(self) -> str:
        """构建HTML内容"""
        market = self.market
        
        # 计算涨跌幅占比
        total = market.up_count + market.down_count + market.flat_count + market.suspension_count
        up_pct = (market.up_count / total * 100) if total > 0 else 0
        down_pct = (market.down_count / total * 100) if total > 0 else 0
        
        # 涨跌停数据
        real_up = market.real_limit_up_count
        one_word_up = max(0, market.limit_up_count - market.real_limit_up_count)
        real_down = market.real_limit_down_count
        one_word_down = max(0, market.limit_down_count - market.real_limit_down_count)
        limit_total = real_up + one_word_up + real_down + one_word_down
        
        # 涨停占比
        up_limit_pct = ((real_up + one_word_up) / limit_total * 100) if limit_total > 0 else 0
        
        # 成交量数据（最近30天）
        volume_data = self.volume_history[-30:] if self.volume_history else []
        volume_labels = [v.date[5:] for v in volume_data]  # MM-DD
        volume_values = [round(v.volume / 100000000) for v in volume_data]  # 转换为亿元
        
        # 涨跌分布数据
        dist_data = [
            {'range': '-20%~-10%', 'down': market.down_10_20, 'up': 0},
            {'range': '-10%~-7%', 'down': market.down_7_10, 'up': 0},
            {'range': '-7%~-5%', 'down': market.down_5_7, 'up': 0},
            {'range': '-5%~-3%', 'down': market.down_3_5, 'up': 0},
            {'range': '-3%~0%', 'down': market.down_0_3, 'up': 0},
            {'range': '0%~3%', 'down': 0, 'up': market.up_0_3},
            {'range': '3%~5%', 'down': 0, 'up': market.up_3_5},
            {'range': '5%~7%', 'down': 0, 'up': market.up_5_7},
            {'range': '7%~10%', 'down': 0, 'up': market.up_7_10},
            {'range': '10%~20%', 'down': 0, 'up': market.up_10_20},
        ]
        
        # 人气排名数据
        rank_data = []
        for i, r in enumerate(self.heat_ranks[:20]):
            rank_data.append({
                'rank': i + 1,
                'code': r.code,
                'name': r.name if r.name else r.code,
                'wencai': r.wencai_rank if r.wencai_rank > 0 else '-',
                'xueqiu': r.xueqiu_rank if r.xueqiu_rank > 0 else '-',
                'dongcai': r.eastmoney_rank if r.eastmoney_rank > 0 else '-',
                'score': round(r.composite_score, 1)
            })
        
        # 新闻资讯热度排名数据
        news_rank_data = []
        for i, r in enumerate(self.news_ranks):
            news_rank_data.append({
                'rank': i + 1,
                'title': r.title,
                'url': r.representative_url,
                'source_count': r.source_count,
                'sources': ', '.join(r.sources) if r.sources else '',
                'score': round(r.composite_score, 1)
            })
        
        # 涨停股票数据
        limit_up_data = []
        sorted_stocks = sorted(self.surge_stocks, key=lambda x: x.change_pct, reverse=True)
        for stock in sorted_stocks:
            limit_up_data.append({
                'code': stock.code,
                'name': stock.name,
                'percent': f"{stock.change_pct:.1f}%",
                'reason': stock.reason if stock.reason else '未知'
            })
        
        # 市场情绪判断
        fear_index = market.fear_index
        greed_index = market.greed_index
        if fear_index > 50:
            sentiment_text = "🔴 市场恐慌情绪较强"
            sentiment_class = "fear"
            sentiment_color = "#ff6b6b"
        elif greed_index > 50:
            sentiment_text = "🟢 市场贪婪情绪较强"
            sentiment_class = "greed"
            sentiment_color = "#51cf66"
        else:
            sentiment_text = "🟡 市场情绪中性"
            sentiment_class = "neutral"
            sentiment_color = "#fcc419"
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股每日复盘报告 - {market.date}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* 头部样式 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            border-radius: 50%;
        }}
        
        .header h1 {{
            color: white;
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
        }}
        
        .header .date {{
            color: rgba(255,255,255,0.8);
            font-size: 1.2em;
            position: relative;
            z-index: 1;
        }}
        
        /* 卡片样式 */
        .card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }}
        
        .card-title {{
            font-size: 1.5em;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .card-title .icon {{
            font-size: 1.3em;
        }}
        
        /* 仪表图网格 */
        .gauge-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}
        
        .gauge-card {{
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .gauge-card-title {{
            font-size: 1.2em;
            font-weight: 700;
            margin-bottom: 15px;
            text-align: center;
            color: #333;
        }}
        
        /* 半圆仪表盘容器 */
        .semi-gauge-container {{
            position: relative;
            width: 100%;
            height: 200px;
            display: flex;
            justify-content: center;
            align-items: flex-end;
        }}
        
        /* 半圆仪表盘 */
        .semi-gauge {{
            position: relative;
            width: 280px;
            height: 140px;
            overflow: hidden;
        }}
        
        .semi-gauge-bg {{
            position: absolute;
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: conic-gradient(from 180deg, 
                #ff6b6b 0deg, 
                #ff6b6b 60deg,
                #ffa94d 60deg,
                #ffa94d 90deg,
                #ffd43b 90deg,
                #ffd43b 120deg,
                #69db7c 120deg,
                #69db7c 180deg
            );
            top: 0;
            left: 0;
        }}
        
        .semi-gauge-bg::after {{
            content: '';
            position: absolute;
            width: 200px;
            height: 200px;
            background: white;
            border-radius: 50%;
            top: 40px;
            left: 40px;
        }}
        
        .semi-gauge-needle {{
            position: absolute;
            width: 4px;
            height: 110px;
            background: #333;
            bottom: 0;
            left: 50%;
            transform-origin: bottom center;
            transform: translateX(-50%) rotate(-90deg);
            border-radius: 2px;
            transition: transform 1.5s cubic-bezier(0.34, 1.56, 0.64, 1);
            z-index: 10;
            mask: radial-gradient(at 50% 100%, transparent 71%, black 72%);
            -webkit-mask: radial-gradient(at 50% 100%, transparent 71%, black 72%);
        }}
        
        .semi-gauge-needle::after {{
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            background: #333;
            border-radius: 50%;
            bottom: -8px;
            left: 50%;
            transform: translateX(-50%);
        }}
        
        .semi-gauge-labels {{
            position: absolute;
            bottom: 0;
            width: 100%;
            display: flex;
            justify-content: space-between;
            padding: 0 20px;
            font-size: 0.8em;
            color: #666;
        }}
        
        .semi-gauge-value {{
            position: absolute;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
        }}
        
        .semi-gauge-value .number {{
            font-size: 2.5em;
            font-weight: 700;
            color: #333;
        }}
        
        .semi-gauge-value .label {{
            font-size: 0.9em;
            color: #666;
        }}
        
        /* 图例 */
        .gauge-legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85em;
        }}
        
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }}
        
        /* 市场统计 */
        .market-gauge-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .market-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            width: 100%;
            margin-top: 15px;
        }}
        
        .market-stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        
        .market-stat-item.up {{
            background: #fff5f5;
            color: #c92a2a;
        }}
        
        .market-stat-item.down {{
            background: #d3f9d8;
            color: #2b8a3e;
        }}
        
        .market-stat-item.neutral {{
            background: #f8f9fa;
            color: #495057;
        }}
        
        /* 涨停/跌停仪表图 */
        .limit-gauge-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .limit-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            width: 100%;
            margin-top: 15px;
        }}
        
        .limit-stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.85em;
        }}
        
        .limit-stat-item.up-normal {{
            background: #fff5f5;
            color: #c92a2a;
            border-left: 3px solid #ff6b6b;
        }}
        
        .limit-stat-item.up-word {{
            background: #ffe3e3;
            color: #c92a2a;
            border-left: 3px solid #fa5252;
        }}
        
        .limit-stat-item.down-normal {{
            background: #d3f9d8;
            color: #2b8a3e;
            border-left: 3px solid #51cf66;
        }}
        
        .limit-stat-item.down-word {{
            background: #b2f2bb;
            color: #2b8a3e;
            border-left: 3px solid #40c057;
        }}
        
        /* 情绪仪表盘 */
        .sentiment-container {{
            display: flex;
            gap: 30px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .gauge-wrapper {{
            flex: 1;
            min-width: 300px;
        }}
        
        .gauge {{
            position: relative;
            width: 100%;
            height: 200px;
            background: conic-gradient(from 180deg, 
                #51cf66 0deg, 
                #51cf66 36deg, 
                #94d82d 36deg, 
                #94d82d 72deg,
                #fcc419 72deg,
                #fcc419 108deg,
                #ff922b 108deg,
                #ff922b 144deg,
                #ff6b6b 144deg,
                #ff6b6b 180deg
            );
            border-radius: 200px 200px 0 0;
            mask: radial-gradient(at 50% 100%, transparent 60%, black 61%);
            -webkit-mask: radial-gradient(at 50% 100%, transparent 60%, black 61%);
        }}
        
        .gauge-needle {{
            position: absolute;
            bottom: 0;
            left: 50%;
            width: 4px;
            height: 180px;
            background: #333;
            transform-origin: bottom center;
            transform: translateX(-50%) rotate(0deg);
            border-radius: 2px;
            transition: transform 1s ease;
            mask: radial-gradient(at 50% 100%, transparent 60%, black 61%);
            -webkit-mask: radial-gradient(at 50% 100%, transparent 60%, black 61%);
        }}
        
        .gauge-center {{
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
        }}
        
        .gauge-value {{
            font-size: 3em;
            font-weight: 700;
        }}
        
        .gauge-label {{
            font-size: 1.2em;
            color: #666;
            margin-top: 5px;
        }}
        
        .sentiment-info {{
            flex: 1;
            min-width: 300px;
        }}
        
        .sentiment-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid;
        }}
        
        .sentiment-item.fear {{
            border-left-color: #ff6b6b;
        }}
        
        .sentiment-item.greed {{
            border-left-color: #51cf66;
        }}
        
        .sentiment-item .label {{
            font-weight: 600;
        }}
        
        .sentiment-item .value {{
            font-size: 1.3em;
            font-weight: 700;
        }}
        
        .sentiment-item.fear .value {{
            color: #ff6b6b;
        }}
        
        .sentiment-item.greed .value {{
            color: #51cf66;
        }}
        
        .sentiment-status {{
            margin-top: 20px;
            padding: 20px;
            background: linear-gradient(135deg, {sentiment_color} 0%, {sentiment_color}dd 100%);
            color: white;
            border-radius: 12px;
            text-align: center;
            font-size: 1.3em;
            font-weight: 600;
        }}
        
        /* 图表容器 */
        .chart-container {{
            position: relative;
            height: 400px;
            margin-top: 20px;
        }}
        
        /* 涨跌分布 */
        .distribution-container {{
            display: flex;
            gap: 20px;
            align-items: flex-end;
            justify-content: center;
            height: 300px;
            padding: 20px;
        }}
        
        .dist-bar {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }}
        
        .dist-bar .bar-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2px;
        }}
        
        .dist-bar .bar-up {{
            width: 40px;
            background: linear-gradient(to top, #ff6b6b, #ff8787);
            border-radius: 4px 4px 0 0;
            transition: all 0.3s ease;
        }}
        
        .dist-bar .bar-down {{
            width: 40px;
            background: linear-gradient(to bottom, #51cf66, #40c057);
            border-radius: 0 0 4px 4px;
            transition: all 0.3s ease;
        }}
        
        .dist-bar:hover .bar-up,
        .dist-bar:hover .bar-down {{
            opacity: 0.8;
            transform: scaleX(1.1);
        }}
        
        .dist-bar .label {{
            font-size: 0.8em;
            color: #666;
            text-align: center;
            white-space: nowrap;
        }}
        
        .dist-bar .value {{
            font-size: 0.9em;
            font-weight: 600;
        }}
        
        .dist-bar .value.up {{
            color: #ff6b6b;
        }}
        
        .dist-bar .value.down {{
            color: #51cf66;
        }}
        
        /* 表格样式 */
        .table-wrapper {{
            overflow-x: auto;
            margin-top: 20px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th {{
            padding: 15px 12px;
            text-align: center;
            font-weight: 600;
            white-space: nowrap;
        }}
        
        td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        tbody tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        tbody tr:nth-child(even):hover {{
            background: #e9ecef;
        }}
        
        .rank-1 {{ background: linear-gradient(135deg, #ffd700, #ffed4e) !important; font-weight: 700; }}
        .rank-2 {{ background: linear-gradient(135deg, #c0c0c0, #e8e8e8) !important; font-weight: 700; }}
        .rank-3 {{ background: linear-gradient(135deg, #cd7f32, #daa520) !important; color: white; font-weight: 700; }}
        
        /* 涨停列表 */
        .limit-up-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .limit-up-card {{
            background: linear-gradient(135deg, #fff5f5 0%, #ffe3e3 100%);
            border-left: 4px solid #ff6b6b;
            border-radius: 10px;
            padding: 15px;
            transition: all 0.3s ease;
        }}
        
        .limit-up-card:hover {{
            transform: translateX(5px);
            box-shadow: 0 5px 20px rgba(255,107,107,0.2);
        }}
        
        .limit-up-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .limit-up-name {{
            font-weight: 700;
            font-size: 1.1em;
        }}
        
        .limit-up-code {{
            color: #666;
            font-size: 0.9em;
        }}
        
        .limit-up-percent {{
            background: #ff6b6b;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 700;
        }}
        
        .limit-up-reason {{
            font-size: 0.85em;
            color: #666;
            line-height: 1.4;
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.7);
            margin-top: 40px;
            padding: 20px;
        }}
        
        /* 指标表格 */
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        .metrics-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: center;
        }}
        
        .metrics-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e9ecef;
            text-align: center;
        }}
        
        .metrics-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        /* 响应式 */
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .gauge-grid {{
                grid-template-columns: 1fr;
            }}
            
            .semi-gauge {{
                width: 240px;
                height: 120px;
            }}
            
            .semi-gauge-bg {{
                width: 240px;
                height: 240px;
            }}
            
            .semi-gauge-bg::after {{
                width: 170px;
                height: 170px;
                top: 35px;
                left: 35px;
            }}
            
            .sentiment-container {{
                flex-direction: column;
            }}
            
            .distribution-container {{
                height: 250px;
            }}
            
            .dist-bar .bar-up,
            .dist-bar .bar-down {{
                width: 30px;
            }}
            
            .limit-up-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>📈 A股每日复盘报告</h1>
            <div class="date">{self._format_date(market.date)} {self._get_weekday(market.date)}</div>
        </div>
        
        <!-- 双仪表图区域 -->
        <div class="gauge-grid">
            <!-- 市场涨跌分布仪表图 -->
            <div class="gauge-card">
                <div class="gauge-card-title">📊 市场涨跌分布</div>
                <div class="market-gauge-wrapper">
                    <div class="semi-gauge-container">
                        <div class="semi-gauge">
                            <div class="semi-gauge-bg"></div>
                            <div class="semi-gauge-needle" id="marketNeedle"></div>
                            <div class="semi-gauge-value">
                                <div class="number" id="marketRatio">{up_pct:.1f}%</div>
                                <div class="label">上涨占比</div>
                            </div>
                        </div>
                    </div>
                    <div class="semi-gauge-labels">
                        <span>0%</span>
                        <span>25%</span>
                        <span>50%</span>
                        <span>75%</span>
                        <span>100%</span>
                    </div>
                    <div class="market-stats">
                        <div class="market-stat-item up">
                            <span>🔴 上涨</span>
                            <strong>{market.up_count:,}</strong>
                        </div>
                        <div class="market-stat-item down">
                            <span>🟢 下跌</span>
                            <strong>{market.down_count:,}</strong>
                        </div>
                        <div class="market-stat-item neutral">
                            <span>⚪ 平盘</span>
                            <strong>{market.flat_count:,}</strong>
                        </div>
                        <div class="market-stat-item neutral">
                            <span>⏸ 停牌</span>
                            <strong>{market.suspension_count:,}</strong>
                        </div>
                    </div>
                    <div class="gauge-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #ff6b6b;"></div>
                            <span>上涨 ({up_pct:.1f}%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #51cf66;"></div>
                            <span>下跌 ({down_pct:.1f}%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #868e96;"></div>
                            <span>平盘+停牌 ({100-up_pct-down_pct:.1f}%)</span>
                        </div>
                    </div>
                    <!-- 指标表格 -->
                    <table class="metrics-table">
                        <tr><th>指标</th><th>数值</th></tr>
                        <tr><td>涨跌比</td><td>{market.rise_fall_ratio * 100:.1f}%</td></tr>
                        <tr><td>涨跌停比</td><td>{market.limit_ratio * 100:.1f}%</td></tr>
                        <tr><td>真实涨跌停比</td><td>{market.real_limit_ratio * 100:.1f}%</td></tr>
                        <tr><td>大盘拥挤度</td><td>{market.congestion:.1f}%</td></tr>
                        <tr><td>市场活跃度</td><td>{market.market_activity:.1f}%</td></tr>
                    </table>
                </div>
            </div>
            
            <!-- 涨停跌停细分分布仪表图 -->
            <div class="gauge-card">
                <div class="gauge-card-title">🎯 涨跌停细分分布</div>
                <div class="limit-gauge-wrapper">
                    <div class="semi-gauge-container">
                        <div class="semi-gauge">
                            <div class="semi-gauge-bg" style="background: conic-gradient(from 180deg, 
                                #ff6b6b 0deg, 
                                #ff6b6b {real_up/limit_total*180 if limit_total > 0 else 45}deg,
                                #ffa94d {real_up/limit_total*180 if limit_total > 0 else 45}deg,
                                #ffa94d {(real_up+one_word_up)/limit_total*180 if limit_total > 0 else 90}deg,
                                #69db7c {(real_up+one_word_up)/limit_total*180 if limit_total > 0 else 90}deg,
                                #69db7c {(real_up+one_word_up+real_down)/limit_total*180 if limit_total > 0 else 135}deg,
                                #339af0 {(real_up+one_word_up+real_down)/limit_total*180 if limit_total > 0 else 135}deg,
                                #339af0 180deg
                            );"></div>
                            <div class="semi-gauge-needle" id="limitNeedle"></div>
                            <div class="semi-gauge-value">
                                <div class="number" id="limitRatio">{up_limit_pct:.1f}%</div>
                                <div class="label">涨停占比</div>
                            </div>
                        </div>
                    </div>
                    <div class="semi-gauge-labels">
                        <span>跌停</span>
                        <span></span>
                        <span>平衡</span>
                        <span></span>
                        <span>涨停</span>
                    </div>
                    <div class="limit-stats">
                        <div class="limit-stat-item up-normal">
                            <span>📈 非一字涨停</span>
                            <strong>{real_up}</strong>
                        </div>
                        <div class="limit-stat-item up-word">
                            <span>🔒 一字涨停</span>
                            <strong>{one_word_up}</strong>
                        </div>
                        <div class="limit-stat-item down-normal">
                            <span>📉 非一字跌停</span>
                            <strong>{real_down}</strong>
                        </div>
                        <div class="limit-stat-item down-word">
                            <span>🔒 一字跌停</span>
                            <strong>{one_word_down}</strong>
                        </div>
                    </div>
                    <div class="gauge-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background: #ff6b6b;"></div>
                            <span>非一字涨停 ({real_up/limit_total*100:.1f}%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #ffa94d;"></div>
                            <span>一字涨停 ({one_word_up/limit_total*100:.1f}%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #69db7c;"></div>
                            <span>非一字跌停 ({real_down/limit_total*100:.1f}%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #339af0;"></div>
                            <span>一字跌停 ({one_word_down/limit_total*100:.1f}%)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 市场情绪 -->
        <div class="card">
            <div class="card-title">
                <span class="icon">🎭</span>
                市场情绪
            </div>
            <div class="sentiment-container">
                <div class="gauge-wrapper">
                    <div style="position: relative; height: 200px;">
                        <div class="gauge"></div>
                        <div class="gauge-needle" id="gaugeNeedle"></div>
                        <div class="gauge-center">
                            <div class="gauge-value" style="color: {sentiment_color};">{fear_index:.1f}</div>
                            <div class="gauge-label">恐慌指数</div>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 10px; padding: 0 20px; font-size: 0.8em; color: #666;">
                        <span>极度贪婪</span>
                        <span>贪婪</span>
                        <span>中性</span>
                        <span>恐惧</span>
                        <span>极度恐惧</span>
                    </div>
                </div>
                <div class="sentiment-info">
                    <div class="sentiment-item fear">
                        <span class="label">恐慌指数</span>
                        <span class="value">{fear_index:.1f}% 🔴</span>
                    </div>
                    <div class="sentiment-item greed">
                        <span class="label">贪婪指数</span>
                        <span class="value">{greed_index:.1f}% 🟡</span>
                    </div>
                    <div class="sentiment-status">
                        {sentiment_text}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 涨跌分布 -->
        <div class="card">
            <div class="card-title">
                <span class="icon">📊</span>
                涨跌分布
            </div>
            <div class="distribution-container" id="distributionChart">
                <!-- 动态生成 -->
            </div>
        </div>
        
        <!-- 成交量趋势 -->
        <div class="card">
            <div class="card-title">
                <span class="icon">📈</span>
                最近30日成交额趋势
            </div>
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
        </div>
        
        <!-- 涨停分析 -->
        <div class="card">
            <div class="card-title">
                <span class="icon">🚀</span>
                涨停分析 ({len(self.surge_stocks)}只)
            </div>
            <div class="limit-up-grid" id="limitUpGrid">
                <!-- 动态生成 -->
            </div>
        </div>
        
        <!-- 人气排名TOP20 -->
        <div class="card">
            <div class="card-title">
                <span class="icon">🔥</span>
                人气排名 TOP20
            </div>
            <div class="table-wrapper">
                <table id="rankTable">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>问财排名</th>
                            <th>雪球排名</th>
                            <th>东财排名</th>
                            <th>热度分</th>
                        </tr>
                    </thead>
                    <tbody id="rankTableBody">
                        <!-- 动态生成 -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 复合资讯热度TOP{len(self.news_ranks)} -->
        <div class="card">
            <div class="card-title">
                <span class="icon">📰</span>
                复合资讯热度 TOP{len(self.news_ranks)}
            </div>
            <div class="table-wrapper">
                <table id="newsRankTable">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>资讯标题</th>
                            <th>来源数</th>
                            <th>来源平台</th>
                            <th>热度分</th>
                        </tr>
                    </thead>
                    <tbody id="newsRankTableBody">
                        <!-- 动态生成 -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin-top: 10px; font-size: 0.9em;">数据仅供参考，投资有风险，入市需谨慎</p>
        </div>
    </div>
    
    <script>
        // 涨跌分布数据
        const distributionData = {json.dumps(dist_data, ensure_ascii=False)};
        
        // 生成涨跌分布图
        const distContainer = document.getElementById('distributionChart');
        const maxValue = Math.max(...distributionData.map(d => Math.max(d.up, d.down)), 1);
        
        distributionData.forEach(item => {{
            const bar = document.createElement('div');
            bar.className = 'dist-bar';
            
            const upHeight = item.up > 0 ? (item.up / maxValue * 150) : 0;
            const downHeight = item.down > 0 ? (item.down / maxValue * 150) : 0;
            
            bar.innerHTML = `
                <div class="value up">${{item.up > 0 ? item.up : ''}}</div>
                <div class="bar-wrapper">
                    <div class="bar-up" style="height: ${{upHeight}}px;"></div>
                    <div class="bar-down" style="height: ${{downHeight}}px;"></div>
                </div>
                <div class="value down">${{item.down > 0 ? item.down : ''}}</div>
                <div class="label">${{item.range}}</div>
            `;
            
            distContainer.appendChild(bar);
        }});
        
        // 成交量数据
        const volumeData = {{
            labels: {json.dumps(volume_labels)},
            values: {json.dumps(volume_values)}
        }};
        
        // 成交量图表
        const ctx = document.getElementById('volumeChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: volumeData.labels,
                datasets: [{{
                    label: '成交额（亿元）',
                    data: volumeData.values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {{
                            label: function(context) {{
                                return context.parsed.y + ' 亿元';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        grid: {{
                            color: 'rgba(0,0,0,0.05)'
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return value + '亿';
                            }}
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
        
        // 涨停数据
        const limitUpData = {json.dumps(limit_up_data, ensure_ascii=False)};
        
        // 生成涨停卡片
        const limitUpGrid = document.getElementById('limitUpGrid');
        limitUpData.forEach(item => {{
            const card = document.createElement('div');
            card.className = 'limit-up-card';
            card.innerHTML = `
                <div class="limit-up-header">
                    <div>
                        <span class="limit-up-name">${{item.name}}</span>
                        <span class="limit-up-code">${{item.code}}</span>
                    </div>
                    <span class="limit-up-percent">${{item.percent}}</span>
                </div>
                <div class="limit-up-reason">${{item.reason}}</div>
            `;
            limitUpGrid.appendChild(card);
        }});
        
        // 人气排名数据
        const rankData = {json.dumps(rank_data, ensure_ascii=False)};
        
        // 生成排名表格
        const rankTableBody = document.getElementById('rankTableBody');
        rankData.forEach(item => {{
            const row = document.createElement('tr');
            if (item.rank <= 3) {{
                row.className = `rank-${{item.rank}}`;
            }}
            row.innerHTML = `
                <td>${{item.rank}}</td>
                <td>${{item.code}}</td>
                <td><strong>${{item.name}}</strong></td>
                <td>${{item.wencai}}</td>
                <td>${{item.xueqiu}}</td>
                <td>${{item.dongcai}}</td>
                <td><strong>${{item.score}}</strong></td>
            `;
            rankTableBody.appendChild(row);
        }});
        
        // 新闻资讯热度排名数据
        const newsRankData = {json.dumps(news_rank_data, ensure_ascii=False)};
        
        // 生成新闻排名表格
        const newsRankTableBody = document.getElementById('newsRankTableBody');
        newsRankData.forEach(item => {{
            const row = document.createElement('tr');
            if (item.rank <= 3) {{
                row.className = `rank-${{item.rank}}`;
            }}
            const titleLink = item.url ? `<a href="${{item.url}}" target="_blank" style="color: #1a73e8; text-decoration: none;">${{item.title}}</a>` : item.title;
            row.innerHTML = `
                <td>${{item.rank}}</td>
                <td style="text-align: left; padding-left: 16px;">${{titleLink}}</td>
                <td>${{item.source_count}}</td>
                <td>${{item.sources}}</td>
                <td><strong>${{item.score}}</strong></td>
            `;
            newsRankTableBody.appendChild(row);
        }});
        
        // 仪表盘动画
        setTimeout(() => {{
            // 市场情绪仪表盘 (恐慌指数)
            const needle = document.getElementById('gaugeNeedle');
            const fearAngle = -90 + ({fear_index} / 100 * 180);
            needle.style.transform = `translateX(-50%) rotate(${{fearAngle}}deg)`;
            
            // 市场涨跌分布仪表盘
            const marketNeedle = document.getElementById('marketNeedle');
            const marketAngle = -90 + ({up_pct} / 100 * 180);
            marketNeedle.style.transform = `translateX(-50%) rotate(${{marketAngle}}deg)`;
            
            // 涨跌停分布仪表盘
            const limitNeedle = document.getElementById('limitNeedle');
            const limitAngle = -90 + ({(real_up + one_word_up) / limit_total * 180 if limit_total > 0 else 90});
            limitNeedle.style.transform = `translateX(-50%) rotate(${{limitAngle}}deg)`;
        }}, 500);
    </script>
</body>
</html>'''
        
        return html