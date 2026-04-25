#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试5：问财数据解析器单元测试
测试_parse_answer方法对各种返回格式的解析能力
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWencaiParser(unittest.TestCase):
    """测试问财数据解析器"""
    
    def setUp(self):
        from fetcher.wencai import WencaiFetcher
        self.fetcher = WencaiFetcher()
    
    def test_parse_standard_response(self):
        """测试标准问财返回格式"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{
                    'txt': [{
                        'content': {
                            'components': [{
                                'data': {
                                    'datas': [
                                        {'股票代码': '600519', '股票简称': '贵州茅台', '涨跌幅': 5.2},
                                        {'股票代码': '000001', '股票简称': '平安银行', '涨跌幅': 3.1},
                                    ]
                                }
                            }]
                        }
                    }]
                }]
            }
        }
        
        result = self.fetcher._parse_answer(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['股票代码'], '600519')
        self.assertEqual(result[1]['股票简称'], '平安银行')
    
    def test_parse_direct_list_response(self):
        """测试直接返回列表格式"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{
                    'txt': [
                        {'股票代码': '600519', '股票简称': '贵州茅台', '涨跌幅': 5.2},
                        {'股票代码': '000001', '股票简称': '平安银行', '涨跌幅': 3.1},
                    ]
                }]
            }
        }
        
        result = self.fetcher._parse_answer(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['股票代码'], '600519')
    
    def test_parse_string_list_response(self):
        """测试字符串列表格式"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{
                    'txt': ['查询结果：上涨3000家，下跌2000家']
                }]
            }
        }
        
        result = self.fetcher._parse_answer(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['result'], '查询结果：上涨3000家，下跌2000家')
    
    def test_parse_no_answer(self):
        """测试无答案返回"""
        data = {'errno': 0, 'data': {}}
        result = self.fetcher._parse_answer(data)
        self.assertEqual(result, [])
    
    def test_parse_empty_txt(self):
        """测试空txt列表"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{'txt': []}]
            }
        }
        result = self.fetcher._parse_answer(data)
        self.assertEqual(result, [])
    
    def test_parse_error_code(self):
        """测试错误码"""
        data = {'errno': -1, 'data': {}}
        result = self.fetcher._parse_answer(data)
        self.assertEqual(result, [])
    
    def test_parse_no_components(self):
        """测试无组件返回"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{
                    'txt': [{
                        'content': {
                            'components': []
                        }
                    }]
                }]
            }
        }
        result = self.fetcher._parse_answer(data)
        self.assertEqual(result, [])
    
    def test_parse_data_as_list(self):
        """测试data直接是列表"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{
                    'txt': [{
                        'content': {
                            'components': [{
                                'data': [
                                    {'股票代码': '600519'},
                                    {'股票代码': '000001'},
                                ]
                            }]
                        }
                    }]
                }]
            }
        }
        
        result = self.fetcher._parse_answer(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['股票代码'], '600519')
    
    def test_parse_datas_in_component(self):
        """测试组件内直接包含datas"""
        data = {
            'errno': 0,
            'data': {
                'answer': [{
                    'txt': [{
                        'content': {
                            'components': [{
                                'datas': [
                                    {'股票代码': '600519'},
                                ]
                            }]
                        }
                    }]
                }]
            }
        }
        
        result = self.fetcher._parse_answer(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['股票代码'], '600519')


if __name__ == '__main__':
    print("=" * 60)
    print("测试5：问财数据解析器单元测试")
    print("=" * 60)
    
    unittest.main(verbosity=2)