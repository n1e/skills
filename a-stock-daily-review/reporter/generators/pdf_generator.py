#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF报告生成器
生成包含图表和仪表盘的PDF格式复盘报告
"""

import os
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Frame, PageTemplate, BaseDocTemplate
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle, Wedge
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

from logger import logger
from models.market import MarketData, VolumeData
from models.stock import SurgeStock
from models.review import DailyReview


# 颜色定义
PRIMARY_COLOR = HexColor('#1a73e8')
SUCCESS_COLOR = HexColor('#ef4444')  # 红色表示上涨
DANGER_COLOR = HexColor('#22c55e')   # 绿色表示下跌
WARNING_COLOR = HexColor('#fbbc04')
BG_COLOR = HexColor('#f8f9fa')
TEXT_COLOR = HexColor('#202124')
LIGHT_GRAY = HexColor('#e8eaed')
DARK_GRAY = HexColor('#5f6368')
FLAT_COLOR = HexColor('#9ca3af')     # 平盘灰色
SUSPEND_COLOR = HexColor('#d1d5db')  # 停牌浅灰
LIMIT_UP_COLOR = HexColor('#cc0000') # 涨停深红
ONE_WORD_UP_COLOR = HexColor('#ff9999')  # 一字涨停浅红
LIMIT_DOWN_COLOR = HexColor('#009900') # 跌停深绿
ONE_WORD_DOWN_COLOR = HexColor('#99ff99')  # 一字跌停浅绿

# 页面设置
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 36
RIGHT_MARGIN = 36
TOP_MARGIN = 36
BOTTOM_MARGIN = 36
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
CONTENT_HEIGHT = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN


class PDFGenerator:
    """PDF报告生成器"""
    
    def __init__(self, output_dir: str = 'output'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._font_name = self._register_fonts()
        self._styles = self._create_styles()
    
    def _register_fonts(self) -> str:
        """注册中文字体"""
        font_candidates = [
            ('ChineseFont', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
            ('Songti', '/System/Library/Fonts/Supplemental/Songti.ttc'),
            ('Heiti', '/System/Library/Fonts/Supplemental/Heiti.ttc'),
            ('PingFang', '/System/Library/Fonts/PingFang.ttc'),
        ]
        
        for font_name, font_path in font_candidates:
            if os.path.exists(font_path):
                try:
                    if font_path.endswith('.ttc'):
                        pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                    else:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                    logger.info(f"使用中文字体: {font_name} ({font_path})")
                    return font_name
                except Exception as e:
                    logger.warning(f"注册字体 {font_name} 失败: {e}")
        
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            logger.info("使用CID中文字体: STSong-Light")
            return 'STSong-Light'
        except Exception as e:
            logger.warning(f"注册CID字体失败: {e}")
            return 'Helvetica'
    
    def _create_styles(self) -> dict:
        """创建样式 - 优化字体大小和清晰度"""
        fn = self._font_name
        
        styles = {
            'title': ParagraphStyle(
                'CustomTitle', fontName=fn, fontSize=24, textColor=PRIMARY_COLOR,
                spaceAfter=6, alignment=TA_CENTER, leading=30
            ),
            'subtitle': ParagraphStyle(
                'CustomSubtitle', fontName=fn, fontSize=12, textColor=DARK_GRAY,
                spaceAfter=12, alignment=TA_CENTER, leading=16
            ),
            'h1': ParagraphStyle(
                'CustomH1', fontName=fn, fontSize=16, textColor=PRIMARY_COLOR,
                spaceBefore=14, spaceAfter=8, leading=20
            ),
            'h2': ParagraphStyle(
                'CustomH2', fontName=fn, fontSize=13, textColor=TEXT_COLOR,
                spaceBefore=10, spaceAfter=6, leading=16
            ),
            'body': ParagraphStyle(
                'CustomBody', fontName=fn, fontSize=10, textColor=TEXT_COLOR,
                spaceAfter=6, leading=14
            ),
            'table_cell': ParagraphStyle(
                'TableCell', fontName=fn, fontSize=9, textColor=TEXT_COLOR,
                alignment=TA_CENTER, leading=12, spaceBefore=2, spaceAfter=2
            ),
            'table_cell_left': ParagraphStyle(
                'TableCellLeft', fontName=fn, fontSize=9, textColor=TEXT_COLOR,
                alignment=TA_LEFT, leading=12, leftIndent=4, spaceBefore=2, spaceAfter=2
            ),
            'table_header': ParagraphStyle(
                'TableHeader', fontName=fn, fontSize=9, textColor=colors.white,
                alignment=TA_CENTER, leading=12, spaceBefore=2, spaceAfter=2
            ),
            'note_text': ParagraphStyle(
                'NoteText', fontName=fn, fontSize=8, textColor=DARK_GRAY,
                alignment=TA_LEFT, leading=11, spaceBefore=3, spaceAfter=3
            ),
            'footer': ParagraphStyle(
                'Footer', fontName=fn, fontSize=8, textColor=DARK_GRAY,
                alignment=TA_CENTER, leading=12
            ),
        }
        
        return styles
    
    def _create_overview_pies(self, market_data: MarketData, width: float = 520, height: float = 200) -> Drawing:
        """创建涨跌饼图 + 涨跌停饼图（横向排列）"""
        drawing = Drawing(width, height)
        fn = self._font_name
        
        # 左侧：涨跌饼图
        data = [
            market_data.up_count, market_data.down_count,
            market_data.flat_count, market_data.suspension_count,
        ]
        labels = ['上涨', '下跌', '平盘', '停牌']
        colors_list = [SUCCESS_COLOR, DANGER_COLOR, FLAT_COLOR, SUSPEND_COLOR]
        
        # 涨跌饼图
        pie1 = Pie()
        pie1.x = 10
        pie1.y = 60
        pie1.width = 130
        pie1.height = 130
        pie1.data = data
        pie1.slices.strokeWidth = 1
        pie1.slices.strokeColor = colors.white
        for i, color in enumerate(colors_list):
            pie1.slices[i].fillColor = color
            pie1.slices[i].fontName = fn
            pie1.slices[i].fontSize = 8
        drawing.add(pie1)
        
        # 涨跌图例
        legend_x1 = 150
        for i, (label, val, color) in enumerate(zip(labels, data, colors_list)):
            y_pos = 175 - (i * 25)
            rect = Rect(legend_x1, y_pos, 12, 12, fillColor=color, strokeColor=LIGHT_GRAY)
            drawing.add(rect)
            text = String(legend_x1 + 16, y_pos + 2, f"{label}: {val}", fontSize=9, fillColor=TEXT_COLOR, fontName=fn)
            drawing.add(text)
        
        # 左侧标题
        title1 = String(75, 40, "涨跌分布", textAnchor='middle', fontSize=11, 
                       fillColor=TEXT_COLOR, fontName=fn)
        drawing.add(title1)
        
        # 右侧：涨跌停饼图
        real_up = market_data.real_limit_up_count
        one_word_up = market_data.limit_up_count - market_data.real_limit_up_count
        if one_word_up < 0:
            one_word_up = 0
        
        real_down = market_data.real_limit_down_count
        one_word_down = market_data.limit_down_count - market_data.real_limit_down_count
        if one_word_down < 0:
            one_word_down = 0
        
        pie2 = Pie()
        pie2.x = 310
        pie2.y = 60
        pie2.width = 130
        pie2.height = 130
        pie2.data = [real_up, one_word_up, real_down, one_word_down]
        pie2.slices.strokeWidth = 1
        pie2.slices.strokeColor = colors.white
        pie2_colors = [LIMIT_UP_COLOR, ONE_WORD_UP_COLOR, LIMIT_DOWN_COLOR, ONE_WORD_DOWN_COLOR]
        for i, color in enumerate(pie2_colors):
            pie2.slices[i].fillColor = color
            pie2.slices[i].fontName = fn
            pie2.slices[i].fontSize = 8
        drawing.add(pie2)
        
        # 涨跌停图例
        legend_x2 = 450
        limit_labels = [('真实涨停', real_up, LIMIT_UP_COLOR), ('一字涨停', one_word_up, ONE_WORD_UP_COLOR),
                       ('真实跌停', real_down, LIMIT_DOWN_COLOR), ('一字跌停', one_word_down, ONE_WORD_DOWN_COLOR)]
        for i, (label, val, color) in enumerate(limit_labels):
            y_pos = 175 - (i * 25)
            rect = Rect(legend_x2, y_pos, 12, 12, fillColor=color, strokeColor=LIGHT_GRAY)
            drawing.add(rect)
            text = String(legend_x2 + 16, y_pos + 2, f"{label}: {val}", fontSize=9, fillColor=TEXT_COLOR, fontName=fn)
            drawing.add(text)
        
        # 右侧标题
        title2 = String(375, 40, "涨跌停分布", textAnchor='middle', fontSize=11,
                       fillColor=TEXT_COLOR, fontName=fn)
        drawing.add(title2)
        
        return drawing
    
    def _create_distribution_chart(self, market_data: MarketData, width: float = 520, height: float = 180) -> Drawing:
        """创建涨跌分布图（从底部向上的柱状图）"""
        drawing = Drawing(width, height)
        fn = self._font_name
        
        # 从左到右按涨幅递增排列
        values = [
            market_data.down_10_20, market_data.down_7_10, market_data.down_5_7,
            market_data.down_3_5, market_data.down_0_3,
            market_data.up_0_3, market_data.up_3_5, market_data.up_5_7,
            market_data.up_7_10, market_data.up_10_20,
        ]
        labels = [
            '-20%~-10%', '-10%~-7%', '-7%~-5%', '-5%~-3%', '-3%~0%',
            '0%~3%', '3%~5%', '5%~7%', '7%~10%', '10%~20%'
        ]
        
        chart_x = 55
        chart_y_base = 40   # Y轴基线（底部）
        chart_y_top = 130   # Y轴顶部
        chart_height = chart_y_top - chart_y_base
        chart_width = width - 70
        
        max_val = max(max(values), 1)
        
        bar_width = chart_width / 11
        gap = bar_width * 0.15
        
        # Y轴网格线（从下往上）
        for i in range(5):
            y = chart_y_base + (chart_height * i / 4)
            line = Line(chart_x, y, chart_x + chart_width, y,
                       strokeColor=LIGHT_GRAY, strokeWidth=0.5)
            drawing.add(line)
            val = max_val * i / 4
            if val > 0:
                y_label = String(chart_x - 8, y - 4, str(int(val)),
                               textAnchor='end', fontSize=7, fillColor=DARK_GRAY)
                drawing.add(y_label)
        
        # 底部基准线（X轴）
        base_line = Line(chart_x, chart_y_base, chart_x + chart_width, chart_y_base,
                        strokeColor=DARK_GRAY, strokeWidth=1)
        drawing.add(base_line)
        
        # 绘制柱状图（从底部向上）
        for i, val in enumerate(values):
            h = (val / max_val) * chart_height if max_val > 0 else 0
            x = chart_x + i * (bar_width + gap)
            bar_color = DANGER_COLOR if i < 5 else SUCCESS_COLOR
            
            # 柱子从Y轴基线向上延伸
            rect = Rect(x, chart_y_base, bar_width, h,
                       fillColor=bar_color, strokeColor=None)
            drawing.add(rect)
            
            # 数值标签在柱子上方
            if val > 0:
                val_str = String(x + bar_width/2, chart_y_base + h + 5, str(val),
                               textAnchor='middle', fontSize=7, fillColor=bar_color)
                drawing.add(val_str)
            
            # X轴标签在底部下方
            x_label = String(x + bar_width/2, chart_y_base - 12, labels[i],
                           textAnchor='middle', fontSize=6, fillColor=DARK_GRAY,
                           fontName=fn)
            drawing.add(x_label)
        
        # 图例
        legend_y = 8
        up_legend = Rect(chart_x, legend_y, 10, 10, fillColor=SUCCESS_COLOR)
        drawing.add(up_legend)
        up_text = String(chart_x + 14, legend_y + 2, "上涨", fontSize=7, fillColor=DARK_GRAY, fontName=fn)
        drawing.add(up_text)
        
        down_legend = Rect(chart_x + 55, legend_y, 10, 10, fillColor=DANGER_COLOR)
        drawing.add(down_legend)
        down_text = String(chart_x + 69, legend_y + 2, "下跌", fontSize=7, fillColor=DARK_GRAY, fontName=fn)
        drawing.add(down_text)
        
        return drawing
    
    def _create_header(self, date: str) -> list:
        """创建报告头部"""
        elements = []
        elements.append(Paragraph("A股每日复盘报告", self._styles['title']))
        elements.append(Paragraph(f"报告日期: {date}", self._styles['subtitle']))
        elements.append(Spacer(1, 8))
        line = Drawing(CONTENT_WIDTH, 2)
        line.add(Rect(0, 0, CONTENT_WIDTH, 2, fillColor=PRIMARY_COLOR, strokeColor=None))
        elements.append(line)
        elements.append(Spacer(1, 10))
        return elements
    
    def _create_market_overview(self, market_data: MarketData) -> list:
        """创建大盘概览（饼图 + 指标表格）"""
        elements = []
        
        elements.append(Paragraph("大盘概览", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        # 涨跌饼图 + 涨跌停饼图
        pie_chart = self._create_overview_pies(market_data, width=CONTENT_WIDTH, height=200)
        elements.append(pie_chart)
        elements.append(Spacer(1, 8))
        
        # 指标表格（所有指标统一用百分数格式）
        rise_fall_pct = market_data.rise_fall_ratio * 100  # 涨跌比转百分数
        limit_ratio_pct = market_data.limit_ratio * 100
        real_limit_pct = market_data.real_limit_ratio * 100
        congestion_pct = market_data.congestion  # 已经是百分数
        activity_pct = market_data.market_activity  # 已经是百分数
        
        detail_data = [[
            Paragraph("指标", self._styles['table_header']),
            Paragraph("数值", self._styles['table_header'])
        ]]
        
        items = [
            ("涨跌比", f"{rise_fall_pct:.1f}%"),
            ("涨跌停比", f"{limit_ratio_pct:.1f}%"),
            ("真实涨跌停比", f"{real_limit_pct:.1f}%"),
            ("大盘拥挤度", f"{congestion_pct:.1f}%"),
            ("市场活跃度", f"{activity_pct:.1f}%"),
        ]
        for label, value in items:
            detail_data.append([
                Paragraph(label, self._styles['table_cell']),
                Paragraph(value, self._styles['table_cell'])
            ])
        
        detail_table = Table(detail_data, colWidths=[150, 120])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self._font_name),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, LIGHT_GRAY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_COLOR]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(detail_table)
        elements.append(Spacer(1, 5))
        
        # 拥挤度说明
        elements.append(Paragraph("注: 大盘拥挤度=成交额排名前5%的个股成交额占全部A股占比", self._styles['note_text']))
        elements.append(Spacer(1, 8))
        
        return elements
    
    def _create_gauge_chart(self, value: float, max_value: float, label: str, color: HexColor) -> Drawing:
        """创建仪表盘图表（进度条）"""
        drawing = Drawing(140, 80)
        fn = self._font_name
        
        cx, cy = 70, 40
        bar_width = 90
        bar_height = 14
        
        pct = (value / max_value) * 100 if max_value > 0 else 0
        
        bg_x = cx - bar_width / 2
        bg_rect = Rect(bg_x, cy, bar_width, bar_height,
                      fillColor=LIGHT_GRAY, strokeColor=None)
        drawing.add(bg_rect)
        
        value_width = bar_width * min(pct, 100) / 100
        if value_width > 0:
            value_rect = Rect(bg_x, cy, value_width, bar_height,
                            fillColor=color, strokeColor=None)
            drawing.add(value_rect)
        
        value_str = String(cx, cy + 25, f"{pct:.1f}%",
                          textAnchor='middle', fontSize=14, fillColor=color)
        drawing.add(value_str)
        
        label_str = String(cx, cy - 15, label,
                          textAnchor='middle', fontSize=9, fillColor=DARK_GRAY,
                          fontName=fn)
        drawing.add(label_str)
        
        return drawing
    
    def _create_sentiment_section(self, market_data: MarketData) -> list:
        """创建市场情绪部分"""
        elements = []
        elements.append(Paragraph("市场情绪", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        # 获取恐惧贪婪指数数据
        fear_index = market_data.fear_index
        greed_index = market_data.greed_index
        
        # 仪表盘
        gauges = Drawing(CONTENT_WIDTH, 100)
        
        # 恐慌指数
        fear_gauge = self._create_gauge_chart(
            fear_index, 100, "恐慌指数",
            DANGER_COLOR if fear_index > 50 else SUCCESS_COLOR
        )
        fear_gauge.translate(30, 5)
        gauges.add(fear_gauge)
        
        # 贪婪指数
        greed_gauge = self._create_gauge_chart(
            greed_index, 100, "贪婪指数",
            SUCCESS_COLOR if greed_index > 50 else DANGER_COLOR
        )
        greed_gauge.translate(180, 5)
        gauges.add(greed_gauge)
        
        # 情绪总结
        if fear_index > 50:
            sentiment = " 市场恐慌情绪较强"
            sentiment_color = DANGER_COLOR
        elif greed_index > 50:
            sentiment = " 市场贪婪情绪较强"
            sentiment_color = SUCCESS_COLOR
        else:
            sentiment = " 市场情绪中性"
            sentiment_color = WARNING_COLOR
        
        sentiment_style = ParagraphStyle('sentiment', fontName=self._font_name,
                                         fontSize=12, textColor=sentiment_color,
                                         alignment=TA_CENTER, spaceBefore=3, spaceAfter=3)
        sentiment_data = [[Paragraph(sentiment, sentiment_style)]]
        sentiment_table = Table(sentiment_data, colWidths=[CONTENT_WIDTH])
        sentiment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_COLOR),
            ('BOX', (0, 0), (-1, -1), 2, sentiment_color),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(gauges)
        elements.append(Spacer(1, 8))
        elements.append(sentiment_table)
        elements.append(Spacer(1, 8))
        
        return elements
    
    def _create_volume_chart(self, volume_history: List[VolumeData], width: float = 520, height: float = 250) -> Drawing:
        """创建成交额趋势图（线性图）"""
        drawing = Drawing(width, height)
        fn = self._font_name
        
        if not volume_history:
            return drawing
        
        # 取最近30天数据
        data = volume_history[-30:]
        
        chart_x = 70
        chart_y_base = 40
        chart_y_top = 190
        chart_height = chart_y_top - chart_y_base
        chart_width = width - 100
        
        # 获取最大值
        max_vol = max(v.volume for v in data) if data else 1
        if max_vol == 0:
            max_vol = 1
        
        # Y轴网格线和标签（添加fontName修复中文乱码）
        for i in range(5):
            y = chart_y_base + (chart_height * i / 4)
            line = Line(chart_x, y, chart_x + chart_width, y,
                       strokeColor=LIGHT_GRAY, strokeWidth=0.5)
            drawing.add(line)
            # 转换为亿元显示
            val = max_vol * i / 4 / 100000000
            y_label = String(chart_x - 10, y - 4, f"{val:.0f}亿",
                           textAnchor='end', fontSize=8, fillColor=DARK_GRAY, fontName=fn)
            drawing.add(y_label)
        
        # Y轴标题
        y_title = String(15, chart_y_base + chart_height / 2, "亿元",
                        textAnchor='middle', fontSize=8, fillColor=DARK_GRAY, fontName=fn)
        drawing.add(y_title)
        
        # 绘制折线
        points = []
        for i, vol_data in enumerate(data):
            x = chart_x + (i / max(len(data) - 1, 1)) * chart_width
            y = chart_y_base + (vol_data.volume / max_vol) * chart_height
            points.append((x, y))
        
        # 绘制连线
        for i in range(len(points) - 1):
            line = Line(points[i][0], points[i][1], points[i+1][0], points[i+1][1],
                       strokeColor=PRIMARY_COLOR, strokeWidth=2)
            drawing.add(line)
        
        # 绘制数据点
        for i, (x, y) in enumerate(points):
            circle = Circle(x, y, 3, fillColor=PRIMARY_COLOR, strokeColor=colors.white, strokeWidth=1)
            drawing.add(circle)
        
        # X轴标签（显示所有日期，每隔几个显示一个）
        if len(data) >= 2:
            # 计算显示间隔，确保标签不重叠
            max_labels = 10  # 最多显示10个日期标签
            interval = max(1, len(data) // max_labels)
            
            for i, vol_data in enumerate(data):
                if i % interval == 0 or i == len(data) - 1:
                    date_str = vol_data.date[5:]  # MM-DD
                    label = String(points[i][0], chart_y_base - 15, date_str,
                                 textAnchor='middle', fontSize=7, fillColor=DARK_GRAY)
                    drawing.add(label)
            
            # 最后一天的成交金额标注（在数据点上方）
            last_x, last_y = points[-1]
            last_vol = data[-1].volume / 100000000  # 转换为亿元
            vol_label = String(last_x, last_y + 15, f"{last_vol:.0f}亿",
                             textAnchor='middle', fontSize=9, fillColor=PRIMARY_COLOR, fontName=fn)
            drawing.add(vol_label)
            
            # 最后一天的高亮点
            highlight = Circle(last_x, last_y, 5, fillColor=None, strokeColor=PRIMARY_COLOR, strokeWidth=2)
            drawing.add(highlight)
        
        # 标题
        title = String(chart_x + chart_width / 2, height - 10, "成交额趋势（近30日）",
                      textAnchor='middle', fontSize=11, fillColor=TEXT_COLOR, fontName=fn)
        drawing.add(title)
        
        return drawing
    
    def _create_volume_section(self, volume_history: List[VolumeData]) -> list:
        """创建成交量部分"""
        elements = []
        elements.append(Paragraph("成交额趋势", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        if volume_history:
            chart = self._create_volume_chart(volume_history, width=CONTENT_WIDTH, height=250)
            elements.append(chart)
            elements.append(Spacer(1, 8))
        else:
            elements.append(Paragraph("暂无成交额数据",
                                      ParagraphStyle('vol', fontName=self._font_name,
                                                    fontSize=10, textColor=DARK_GRAY)))
        
        return elements
    
    def _create_distribution_section(self, market_data: MarketData) -> list:
        """创建涨跌分布部分"""
        elements = []
        elements.append(Paragraph("涨跌分布", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        chart = self._create_distribution_chart(market_data, width=CONTENT_WIDTH, height=180)
        elements.append(chart)
        elements.append(Spacer(1, 8))
        
        return elements
    
    def _create_heat_rank_section(self, heat_ranks) -> list:
        """创建人气排名部分"""
        elements = []
        if not heat_ranks:
            return elements
        
        elements.append(Paragraph("人气排名TOP50", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        rank_data = [[
            Paragraph("排名", self._styles['table_header']),
            Paragraph("代码", self._styles['table_header']),
            Paragraph("名称", self._styles['table_header']),
            Paragraph("问财", self._styles['table_header']),
            Paragraph("雪球", self._styles['table_header']),
            Paragraph("东财", self._styles['table_header']),
            Paragraph("热度分", self._styles['table_header'])
        ]]
        for i, r in enumerate(heat_ranks[:50]):
            wc = str(r.wencai_rank) if r.wencai_rank > 0 else "-"
            xq = str(r.xueqiu_rank) if r.xueqiu_rank > 0 else "-"
            em = str(r.eastmoney_rank) if r.eastmoney_rank > 0 else "-"
            name = r.name if r.name else r.code  # 如果名称缺失，使用代码
            rank_data.append([
                Paragraph(str(i+1), self._styles['table_cell']),
                Paragraph(r.code, self._styles['table_cell']),
                Paragraph(name, self._styles['table_cell_left']),
                Paragraph(wc, self._styles['table_cell']),
                Paragraph(xq, self._styles['table_cell']),
                Paragraph(em, self._styles['table_cell']),
                Paragraph(f"{r.composite_score:.1f}", self._styles['table_cell'])
            ])
        
        rank_table = Table(rank_data, colWidths=[40, 60, 85, 50, 50, 50, 65])
        rank_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self._font_name),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, LIGHT_GRAY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_COLOR]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(rank_table)
        elements.append(Spacer(1, 8))
        
        return elements
    
    def _create_news_rank_section(self, news_ranks) -> list:
        """创建新闻资讯热度排名部分"""
        elements = []
        if not news_ranks:
            return elements
        
        elements.append(Paragraph("复合资讯热度TOP30", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        news_data = [[
            Paragraph("排名", self._styles['table_header']),
            Paragraph("资讯标题", self._styles['table_header']),
            Paragraph("来源数", self._styles['table_header']),
            Paragraph("来源平台", self._styles['table_header']),
            Paragraph("热度分", self._styles['table_header'])
        ]]
        for i, r in enumerate(news_ranks[:30]):
            title = r.title[:35] + "..." if len(r.title) > 35 else r.title
            sources = ', '.join(r.sources) if r.sources else ''
            sources = sources[:15] + "..." if len(sources) > 15 else sources
            news_data.append([
                Paragraph(str(i+1), self._styles['table_cell']),
                Paragraph(title, self._styles['table_cell_left']),
                Paragraph(str(r.source_count), self._styles['table_cell']),
                Paragraph(sources, self._styles['table_cell_left']),
                Paragraph(f"{r.composite_score:.1f}", self._styles['table_cell'])
            ])
        
        news_table = Table(news_data, colWidths=[40, 180, 50, 120, 60])
        news_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self._font_name),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, LIGHT_GRAY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_COLOR]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(news_table)
        elements.append(Spacer(1, 8))
        
        return elements
    
    def _analyze_surge_reasons(self, surge_stocks: List[SurgeStock]) -> List[tuple]:
        """分析涨停原因，统计概念标签频次"""
        tag_counter = Counter()
        for stock in surge_stocks:
            reason = stock.reason or ""
            if reason:
                tags = [tag.strip() for tag in reason.split('+') if tag.strip()]
                tag_counter.update(tags)
        return tag_counter.most_common()
    
    def _create_surge_section(self, surge_stocks: List[SurgeStock]) -> list:
        """创建涨停分析部分"""
        elements = []
        if not surge_stocks:
            return elements
        
        elements.append(Paragraph(f"涨停分析 ({len(surge_stocks)}只)", self._styles['h1']))
        elements.append(Spacer(1, 8))
        
        # 涨停股票列表
        elements.append(Paragraph("涨停股票列表", self._styles['h2']))
        
        stock_data = [[
            Paragraph("代码", self._styles['table_header']),
            Paragraph("名称", self._styles['table_header']),
            Paragraph("涨幅", self._styles['table_header']),
            Paragraph("涨停原因", self._styles['table_header'])
        ]]
        sorted_stocks = sorted(surge_stocks, key=lambda x: x.change_pct, reverse=True)
        for stock in sorted_stocks[:50]:
            reason = stock.reason or ""
            if len(reason) > 40:
                reason = reason[:40] + "..."
            stock_data.append([
                Paragraph(stock.code, self._styles['table_cell']),
                Paragraph(stock.name, self._styles['table_cell_left']),
                Paragraph(f"{stock.change_pct:.1f}%", self._styles['table_cell']),
                Paragraph(reason, self._styles['table_cell_left'])
            ])
        
        stock_table = Table(stock_data, colWidths=[60, 80, 50, 280])
        stock_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self._font_name),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, LIGHT_GRAY),
            ('ALIGN', (0, 0), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_COLOR]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(stock_table)
        elements.append(Spacer(1, 10))
        
        # 涨停原因统计
        elements.append(Paragraph("涨停原因分布", self._styles['h2']))
        tag_stats = self._analyze_surge_reasons(surge_stocks)
        
        if tag_stats:
            reason_data = [[
                Paragraph("概念标签", self._styles['table_header']),
                Paragraph("出现次数", self._styles['table_header'])
            ]]
            for tag, count in tag_stats[:20]:
                reason_data.append([
                    Paragraph(tag, self._styles['table_cell_left']),
                    Paragraph(f"{count}次", self._styles['table_cell'])
                ])
            
            reason_table = Table(reason_data, colWidths=[250, 100])
            reason_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), self._font_name),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, LIGHT_GRAY),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_COLOR]),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(reason_table)
        
        elements.append(Spacer(1, 8))
        return elements
    
    def generate(self, review: DailyReview) -> str:
        """生成PDF报告"""
        elements = []
        
        elements.extend(self._create_header(review.date))
        elements.extend(self._create_market_overview(review.market))
        elements.extend(self._create_sentiment_section(review.market))
        elements.extend(self._create_volume_section(review.volume_history))
        elements.extend(self._create_distribution_section(review.market))
        elements.extend(self._create_heat_rank_section(review.heat_ranks))
        elements.extend(self._create_news_rank_section(review.news_ranks))
        elements.extend(self._create_surge_section(review.surge_stocks))
        
        elements.append(Spacer(1, 12))
        line = Drawing(CONTENT_WIDTH, 1)
        line.add(Rect(0, 0, CONTENT_WIDTH, 1, fillColor=LIGHT_GRAY, strokeColor=None))
        elements.append(line)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self._styles['footer']
        ))
        
        output_path = os.path.join(self.output_dir, f"review_{review.date}.pdf")
        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            rightMargin=RIGHT_MARGIN, leftMargin=LEFT_MARGIN, 
            topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN,
            title=f"A股每日复盘报告 - {review.date}", author="A股复盘系统"
        )
        
        doc.build(elements)
        logger.info(f"PDF报告已生成: {output_path}")
        return output_path