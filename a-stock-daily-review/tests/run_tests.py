#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本
运行所有单元测试
"""

import sys
import os
import unittest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有测试模块
from tests.test_03_core_modules import (
    TestMarketData,
    TestStockModels,
    TestConfig,
    TestRetryMechanism,
    TestHelpers,
    TestDailyReview,
    TestHeatRanker,
)

from tests.test_04_report_generators import (
    TestValidators,
    TestTemplateRenderer,
    TestMarkdownGenerator,
    TestJsonGenerator,
    TestReasonAnalyzer,
)

from tests.test_05_wencai_parser import (
    TestWencaiParser,
)

from tests.test_06_legu_fetcher import (
    TestLeguParser,
)


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("  A股每日复盘 - 完整单元测试")
    print("=" * 70)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestMarketData,
        TestStockModels,
        TestConfig,
        TestRetryMechanism,
        TestHelpers,
        TestDailyReview,
        TestHeatRanker,
        TestValidators,
        TestTemplateRenderer,
        TestMarkdownGenerator,
        TestJsonGenerator,
        TestReasonAnalyzer,
        TestWencaiParser,
        TestLeguParser,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "=" * 70)
    print("  测试总结")
    print("=" * 70)
    print(f"  总测试数: {result.testsRun}")
    print(f"  通过:     {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败:     {len(result.failures)}")
    print(f"  错误:     {len(result.errors)}")
    print("=" * 70)
    
    if result.failures:
        print("\n失败详情:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n错误详情:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # 返回是否所有测试通过
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)