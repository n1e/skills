#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试3：核心模块单元测试
测试数据模型、配置、工具函数等
"""

import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMarketData(unittest.TestCase):
    """测试MarketData模型"""
    
    def setUp(self):
        from models.market import MarketData
        self.market = MarketData()
    
    def test_default_values(self):
        """测试默认值"""
        self.assertEqual(self.market.up_count, 0)
        self.assertEqual(self.market.down_count, 0)
        self.assertEqual(self.market.limit_up_count, 0)
        self.assertEqual(self.market.limit_down_count, 0)
        self.assertEqual(self.market.suspension_count, 0)
        self.assertEqual(self.market.real_limit_up_count, 0)
        self.assertEqual(self.market.real_limit_down_count, 0)
    
    def test_rise_fall_ratio(self):
        """测试涨跌比计算"""
        self.market.up_count = 2000
        self.market.down_count = 1000
        self.assertEqual(self.market.rise_fall_ratio, 2.0)
        
        # 测试除零情况
        self.market.down_count = 0
        self.assertEqual(self.market.rise_fall_ratio, 2000.0)
    
    def test_limit_ratio(self):
        """测试涨跌停比"""
        self.market.limit_up_count = 40
        self.market.limit_down_count = 10
        self.assertEqual(self.market.limit_ratio, 4.0)
        
        # 测试除零情况
        self.market.limit_down_count = 0
        self.assertEqual(self.market.limit_ratio, 40.0)
    
    def test_fear_index(self):
        """测试恐慌指数"""
        self.market.limit_up_count = 80
        self.market.limit_down_count = 20
        self.assertAlmostEqual(self.market.fear_index, 20.0, places=1)
        
        # 测试除零情况
        self.market.limit_up_count = 0
        self.market.limit_down_count = 0
        self.assertEqual(self.market.fear_index, 0.0)
    
    def test_greed_index(self):
        """测试贪心指数"""
        self.market.limit_up_count = 80
        self.market.limit_down_count = 20
        self.assertAlmostEqual(self.market.greed_index, 80.0, places=1)
        
        # 测试除零情况
        self.market.limit_up_count = 0
        self.market.limit_down_count = 0
        self.assertEqual(self.market.greed_index, 0.0)
    
    def test_congestion(self):
        """测试大盘拥挤度"""
        self.market.limit_up_count = 100
        self.market.limit_down_count = 20
        self.market.real_limit_up_count = 80
        self.market.real_limit_down_count = 16
        # 拥挤度 = (80+16)/(100+20) = 96/120 = 80%
        self.assertAlmostEqual(self.market.congestion, 80.0, places=1)
        
        # 全部是一字板的情况
        self.market.real_limit_up_count = 0
        self.market.real_limit_down_count = 0
        self.assertEqual(self.market.congestion, 0.0)
        
        # 测试除零情况
        self.market.limit_up_count = 0
        self.market.limit_down_count = 0
        self.assertEqual(self.market.congestion, 0.0)
    
    def test_market_activity(self):
        """测试市场活跃度"""
        self.market.up_count = 2000
        self.market.down_count = 1000
        self.market.flat_count = 100
        self.market.total_count = 3100
        self.market.limit_up_count = 50
        self.market.limit_down_count = 10
        # 活跃度 = (50+10)/3100 = 60/3100 ≈ 1.94%
        self.assertAlmostEqual(self.market.market_activity, 1.94, places=1)
        
        # 测试除零情况
        self.market.total_count = 0
        self.assertEqual(self.market.market_activity, 0.0)
    
    def test_real_limit_ratio(self):
        """测试真实涨跌停比"""
        self.market.real_limit_up_count = 40
        self.market.real_limit_down_count = 10
        self.assertEqual(self.market.real_limit_ratio, 4.0)
        
        # 测试除零情况
        self.market.real_limit_down_count = 0
        self.assertEqual(self.market.real_limit_ratio, 40.0)


class TestStockModels(unittest.TestCase):
    """测试股票模型"""
    
    def test_surge_stock(self):
        """测试SurgeStock"""
        from models.stock import SurgeStock
        stock = SurgeStock(
            code='000001',
            name='平安银行',
            price=15.5,
            change_pct=10.0,
            reason='业绩预增'
        )
        self.assertEqual(stock.code, '000001')
        self.assertEqual(stock.name, '平安银行')
        self.assertEqual(stock.change_pct, 10.0)
    
    def test_heat_rank(self):
        """测试HeatRank"""
        from models.stock import HeatRank
        rank = HeatRank(
            code='000001',
            name='平安银行',
            rank=1,
            heat_score=100,
            source='wencai'
        )
        self.assertEqual(rank.rank, 1)
        self.assertEqual(rank.source, 'wencai')
    
    def test_composite_heat_rank(self):
        """测试CompositeHeatRank"""
        from models.stock import CompositeHeatRank
        rank = CompositeHeatRank(
            code='000001',
            name='平安银行',
            wencai_rank=5,
            xueqiu_rank=10,
            eastmoney_rank=8,
            thsi_rank=3,
            appear_count=4
        )
        self.assertEqual(rank.appear_count, 4)
        self.assertTrue(rank.composite_score >= 0)


class TestConfig(unittest.TestCase):
    """测试配置加载器"""
    
    def test_config_load(self):
        """测试配置加载"""
        from config import config
        self.assertIsNotNone(config)
        
        # 测试基本配置
        self.assertEqual(config.get('output_dir'), 'output')
        self.assertEqual(config.get('run_time'), '16:00')
    
    def test_config_nested(self):
        """测试嵌套配置"""
        from config import config
        self.assertEqual(config.get('surge.min_change_pct'), 9.5)
        self.assertEqual(config.get('heat_rank.top'), 50)
    
    def test_config_default(self):
        """测试默认值"""
        from config import config
        self.assertEqual(config.get('nonexistent', 'default'), 'default')
    
    def test_config_set(self):
        """测试配置设置"""
        from config import Config
        c = Config()
        c.set('test.key', 'value')
        self.assertEqual(c.get('test.key'), 'value')


class TestRetryMechanism(unittest.TestCase):
    """测试重试机制"""
    
    def test_simple_retry(self):
        """测试简单重试"""
        from utils.retry import simple_retry
        
        call_count = 0
        
        @simple_retry(max_attempts=3, delay=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"第{call_count}次失败")
            return "success"
        
        result = failing_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_retry_with_backoff(self):
        """测试指数退避重试"""
        from utils.retry import retry_with_backoff
        
        call_count = 0
        
        @retry_with_backoff(initial_delay=0.1, max_delay=1.0, max_attempts=3)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Always fails")
        
        with self.assertRaises(RuntimeError):
            always_fail()
        
        self.assertEqual(call_count, 3)


class TestHelpers(unittest.TestCase):
    """测试工具函数"""
    
    def test_rand_string(self):
        """测试随机字符串生成"""
        from utils.helpers import rand_string
        s = rand_string(10)
        self.assertEqual(len(s), 10)
        self.assertTrue(s.isalnum())
    
    def test_format_number(self):
        """测试数字格式化"""
        from utils.helpers import format_number
        self.assertEqual(format_number(1234567), '1,234,567')
        # format_number默认precision=0，所以12.345会格式化为整数形式
        self.assertEqual(format_number(12.345, unit='万'), '12万')
        # 带精度测试
        self.assertEqual(format_number(12.345, unit='万', precision=3), '12.345万')
    
    def test_safe_divide(self):
        """测试安全除法"""
        from utils.helpers import safe_divide
        self.assertEqual(safe_divide(10, 2), 5.0)
        self.assertEqual(safe_divide(10, 0), 0.0)
        self.assertEqual(safe_divide(10, 0, default=-1), -1)
    
    def test_truncate_string(self):
        """测试字符串截断"""
        from utils.helpers import truncate_string
        # max_length=5, suffix='...', 所以可保留 5-3=2 个字符
        self.assertEqual(truncate_string('hello world', 5), 'he...')
        self.assertEqual(truncate_string('hi', 5), 'hi')
        self.assertEqual(truncate_string('', 5), '')


class TestDailyReview(unittest.TestCase):
    """测试DailyReview模型"""
    
    def test_daily_review(self):
        """测试每日复盘模型"""
        from models.review import DailyReview
        from models.market import MarketData
        
        review = DailyReview()
        review.date = '2026-04-05'
        review.market = MarketData(up_count=2000, down_count=1000)
        
        self.assertEqual(review.date, '2026-04-05')
        self.assertEqual(review.market.up_count, 2000)
        self.assertGreater(review.market.rise_fall_ratio, 1.0)


class TestHeatRanker(unittest.TestCase):
    """测试热度排名分析器"""
    
    def test_composite_heat_calculation(self):
        """测试复合热度计算"""
        from analyzer.heat_ranker import HeatRanker
        
        wencai = [{'code': '000001', 'name': '平安银行', 'rank': 1, 'heat_score': 99}]
        xueqiu = [{'code': '000001', 'name': '平安银行', 'rank': 2, 'heat_score': 98}]
        eastmoney = [{'code': '000001', 'name': '平安银行', 'rank': 3, 'heat_score': 97}]
        
        result = HeatRanker.calculate_composite_heat(wencai, xueqiu, eastmoney, top=10)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].code, '000001')
        self.assertEqual(result[0].wencai_rank, 1)
        self.assertTrue(result[0].composite_score > 0)


if __name__ == '__main__':
    # 运行所有测试
    print("=" * 60)
    print("测试3：核心模块单元测试")
    print("=" * 60)
    
    unittest.main(verbosity=2)