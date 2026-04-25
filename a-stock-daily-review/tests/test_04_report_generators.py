#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试4：报告生成器单元测试
测试Markdown生成器、JSON生成器、模板渲染器、验证器等
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestValidators(unittest.TestCase):
    """测试验证器"""
    
    def test_normalize_stock_code(self):
        """测试股票代码标准化"""
        from utils.validators import normalize_stock_code
        
        self.assertEqual(normalize_stock_code('SH600519'), '600519')
        self.assertEqual(normalize_stock_code('SZ000001'), '000001')
        self.assertEqual(normalize_stock_code('600519'), '600519')
        self.assertEqual(normalize_stock_code(''), '')
        self.assertEqual(normalize_stock_code(None), '')
    
    def test_is_valid_stock_code(self):
        """测试股票代码验证"""
        from utils.validators import is_valid_stock_code
        
        self.assertTrue(is_valid_stock_code('600519'))
        self.assertTrue(is_valid_stock_code('SH600519'))
        self.assertTrue(is_valid_stock_code('000001'))
        self.assertFalse(is_valid_stock_code('123'))  # 不是6位
        self.assertFalse(is_valid_stock_code(''))
        self.assertFalse(is_valid_stock_code('abc'))
    
    def test_split_market_prefix(self):
        """测试市场前缀分离"""
        from utils.validators import split_market_prefix
        
        self.assertEqual(split_market_prefix('SH600519'), ('SH', '600519'))
        self.assertEqual(split_market_prefix('SZ000001'), ('SZ', '000001'))
        self.assertEqual(split_market_prefix('600519'), ('', '600519'))
    
    def test_format_code_with_prefix(self):
        """测试代码格式化"""
        from utils.validators import format_code_with_prefix
        
        self.assertEqual(format_code_with_prefix('600519', 'SH'), 'SH600519')
        self.assertEqual(format_code_with_prefix('600519'), 'SH600519')  # 自动判断
        self.assertEqual(format_code_with_prefix('000001'), 'SZ000001')  # 自动判断
        self.assertEqual(format_code_with_prefix(''), '')


class TestTemplateRenderer(unittest.TestCase):
    """测试模板渲染器"""
    
    def setUp(self):
        from reporter.template_renderer import TemplateRenderer
        from models.market import MarketData
        from models.stock import SurgeStock, CompositeHeatRank
        
        self.renderer = TemplateRenderer()
        
        # 创建测试数据
        self.market_data = MarketData(
            date='2026-04-05',
            up_count=2500,
            down_count=1500,
            flat_count=100,
            limit_up_count=50,
            limit_down_count=10,
            total_volume=5000000,
            main_inflow=100000
        )
        
        self.surge_stocks = [
            SurgeStock(code='000001', name='平安银行', change_pct=10.0, reason='业绩预增', reason_category='业绩预增'),
            SurgeStock(code='600519', name='贵州茅台', change_pct=9.98, reason='并购重组', reason_category='并购重组'),
        ]
        
        self.heat_ranks = [
            CompositeHeatRank(code='000001', name='平安银行', wencai_rank=1, xueqiu_rank=2, composite_score=95.0),
            CompositeHeatRank(code='600519', name='贵州茅台', wencai_rank=3, eastmoney_rank=5, composite_score=88.0),
        ]
    
    def test_render_market_summary(self):
        """测试大盘概况渲染"""
        result = self.renderer.render_market_summary(self.market_data)
        self.assertIn('上涨家数', result)
        self.assertIn('2500', result)
        self.assertIn('1500', result)
        self.assertIn('50', result)
    
    def test_render_market_sentiment(self):
        """测试市场情绪渲染"""
        result = self.renderer.render_market_sentiment(self.market_data)
        self.assertIn('恐慌指数', result)
        self.assertIn('贪婪指数', result)  # 更新为贪婪指数
        self.assertIn('🟢', result)  # 贪婪情绪
    
    def test_render_heat_ranks(self):
        """测试人气排名渲染"""
        result = self.renderer.render_heat_ranks(self.heat_ranks)
        self.assertIn('平安银行', result)
        self.assertIn('贵州茅台', result)
        self.assertIn('问财排名', result)  # 更新为问财
        self.assertIn('雪球排名', result)
    
    def test_render_surge_analysis(self):
        """测试涨停分析渲染"""
        result = self.renderer.render_surge_analysis(self.surge_stocks)
        self.assertIn('平安银行', result)
        self.assertIn('贵州茅台', result)
        self.assertIn('业绩预增', result)
        self.assertIn('并购重组', result)


class TestMarkdownGenerator(unittest.TestCase):
    """测试Markdown报告生成器"""
    
    def setUp(self):
        from models.review import DailyReview
        from models.market import MarketData, VolumeData
        from models.stock import SurgeStock, CompositeHeatRank
        
        # 创建完整的复盘数据
        self.review = DailyReview()
        self.review.date = '2026-04-05'
        self.review.market = MarketData(
            up_count=2500,
            down_count=1500,
            limit_up_count=50,
            limit_down_count=10
        )
        self.review.volume_history = [
            VolumeData(date='2026-04-01', volume=5000000),
            VolumeData(date='2026-04-02', volume=5500000),
            VolumeData(date='2026-04-03', volume=6000000),
        ]
        self.review.surge_stocks = [
            SurgeStock(code='000001', name='平安银行', change_pct=10.0, reason='业绩预增'),
        ]
        self.review.heat_ranks = [
            CompositeHeatRank(code='000001', name='平安银行', wencai_rank=1, composite_score=95.0),
        ]
    
    def test_generate_markdown(self):
        """测试Markdown报告生成"""
        from reporter.generators import MarkdownGenerator
        
        generator = MarkdownGenerator(self.review)
        result = generator.generate()
        
        # 检查报告结构
        self.assertIn('# A股每日复盘报告', result)
        self.assertIn('2026-04-05', result)
        self.assertIn('## 📊 大盘概况', result)
        self.assertIn('## 🎭 市场情绪', result)
        self.assertIn('## 🚀 涨停分析', result)
        self.assertIn('## 🔥 人气排名TOP50', result)
        self.assertIn('平安银行', result)


class TestJsonGenerator(unittest.TestCase):
    """测试JSON报告生成器"""
    
    def setUp(self):
        from models.review import DailyReview
        from models.market import MarketData, VolumeData
        from models.stock import SurgeStock, CompositeHeatRank
        
        # 创建完整的复盘数据
        self.review = DailyReview()
        self.review.date = '2026-04-05'
        self.review.market = MarketData(
            up_count=2500,
            down_count=1500,
            limit_up_count=50,
            limit_down_count=10
        )
        self.review.volume_history = [
            VolumeData(date='2026-04-01', volume=5000000),
        ]
        self.review.surge_stocks = [
            SurgeStock(code='000001', name='平安银行', change_pct=10.0, reason='业绩预增'),
        ]
        self.review.heat_ranks = [
            CompositeHeatRank(code='000001', name='平安银行', wencai_rank=1, composite_score=95.0),
        ]
    
    def test_generate_json(self):
        """测试JSON报告生成"""
        from reporter.generators import JsonGenerator
        
        generator = JsonGenerator(self.review)
        result = generator.generate()
        
        # 解析JSON验证结构
        data = json.loads(result)
        
        self.assertEqual(data['date'], '2026-04-05')
        self.assertIn('market', data)
        self.assertIn('surge_stocks', data)
        self.assertIn('heat_ranks', data)
        self.assertEqual(data['market']['up_count'], 2500)
        self.assertEqual(len(data['surge_stocks']), 1)
        self.assertEqual(data['surge_stocks'][0]['code'], '000001')


class TestReasonAnalyzer(unittest.TestCase):
    """测试涨停原因分析器"""
    
    def test_analyze(self):
        """测试原因分析"""
        from analyzer.reason_analyzer import ReasonAnalyzer
        
        # 业绩相关
        self.assertEqual(ReasonAnalyzer.analyze('业绩预增带动股价上涨'), '业绩预增')
        self.assertEqual(ReasonAnalyzer.analyze('利润大幅增长'), '业绩预增')
        
        # 并购重组
        self.assertEqual(ReasonAnalyzer.analyze('公司拟收购资产'), '并购重组')
        self.assertEqual(ReasonAnalyzer.analyze('股权转让'), '并购重组')
        
        # 政策利好
        self.assertEqual(ReasonAnalyzer.analyze('政策支持新能源发展'), '政策利好')
        
        # 概念炒作
        self.assertEqual(ReasonAnalyzer.analyze('人工智能概念'), '概念炒作')
        
        # 资金推动
        self.assertEqual(ReasonAnalyzer.analyze('主力资金大幅流入'), '资金推动')
        
        # 技术突破
        self.assertEqual(ReasonAnalyzer.analyze('股价突破历史新高'), '技术突破')
        
        # 行业景气
        self.assertEqual(ReasonAnalyzer.analyze('行业景气度回升'), '行业景气')
        
        # 默认
        self.assertEqual(ReasonAnalyzer.analyze(''), '其他')
        self.assertEqual(ReasonAnalyzer.analyze('未知原因'), '其他')


if __name__ == '__main__':
    # 运行所有测试
    print("=" * 60)
    print("测试4：报告生成器单元测试")
    print("=" * 60)
    
    unittest.main(verbosity=2)