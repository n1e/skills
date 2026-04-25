#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试6：乐股采集器单元测试
测试 LeguFetcher 的 HTML 解析功能
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLeguParser(unittest.TestCase):
    """测试乐股数据解析器"""

    def setUp(self):
        from fetcher.legu import LeguFetcher
        self.fetcher = LeguFetcher()

    def test_parse_market_activity_success(self):
        """测试解析市场活跃度 - 成功 (HTML表格回退)"""
        html = '''
        <html>
            <h4>涨跌比: 69.44%</h4>
            <div class="market-activity-chart-right-side">
                <table>
                    <tbody>
                        <tr>
                            <td class="color-red">3435</td>
                            <td class="color-green">1332</td>
                            <td class="color-gray">175</td>
                        </tr>
                        <tr>
                            <td class="color-red">36</td>
                            <td class="color-green">3</td>
                            <td class="color-gray">5</td>
                        </tr>
                        <tr>
                            <td class="color-red">34</td>
                            <td class="color-green">1</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </html>
        '''
        result = self.fetcher._parse_market_activity(html)

        self.assertIsNotNone(result)
        self.assertEqual(result['up_count'], '3435')
        self.assertEqual(result['down_count'], '1332')
        self.assertEqual(result['flat_count'], '175')
        self.assertEqual(result['limit_up_count'], '36')
        self.assertEqual(result['limit_down_count'], '3')
        self.assertEqual(result['suspension_count'], '5')
        self.assertEqual(result['real_limit_up_count'], '34')
        self.assertEqual(result['real_limit_down_count'], '1')

    def test_parse_market_activity_no_data(self):
        """测试解析市场活跃度 - 无数据"""
        html = '<html><body>无数据</body></html>'
        result = self.fetcher._parse_market_activity(html)
        self.assertIsNone(result)

    def test_parse_market_activity_partial_data(self):
        """测试解析市场活跃度 - 数据不完整"""
        html = '''
        <html>
            <h4>涨跌比: 50.00%</h4>
            <div>
                <td class="color-red">100</td>
            </div>
        </html>
        '''
        result = self.fetcher._parse_market_activity(html)
        # 数据不完整应返回 None
        self.assertIsNone(result)

    def test_parse_congestion_success(self):
        """测试解析拥挤度 - 成功"""
        html = '''
        <html>
            <div class="data-view-head-ashares-congestion">拥挤度: 43.92%</div>
        </html>
        '''
        result = self.fetcher._parse_congestion(html)
        self.assertEqual(result, '拥挤度: 43.92%')

    def test_parse_congestion_no_data(self):
        """测试解析拥挤度 - 无数据"""
        html = '<html><body>无数据</body></html>'
        result = self.fetcher._parse_congestion(html)
        self.assertIsNone(result)


if __name__ == '__main__':
    print("=" * 60)
    print("测试6：乐股采集器单元测试")
    print("=" * 60)

    unittest.main(verbosity=2)