#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐股数据采集器
从 legulegu.com 获取大盘涨跌统计、拥挤度等数据
"""

import re
from typing import Dict, Optional

import requests

from logger import logger
from utils.retry import retry_with_backoff


class LeguFetcher:
    """乐股数据采集器"""

    MARKET_ACTIVITY_URL = "https://legulegu.com/stockdata/market-activity"
    MARKET_CONGESTION_URL = "https://legulegu.com/stockdata/ashares-congestion"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'legulegu.com',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
        })

    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def fetch_market_activity(self) -> Optional[Dict]:
        """
        获取市场活跃度数据

        Returns:
            包含涨跌统计的字典，例如：
            {
                'rise_fall_ratio': '涨跌比: 69.44%',
                'rise_count': '3435',
                'fall_count': '1332',
                'flat_count': '175',
                'raising_limit_count': '36',
                'limit_down_count': '3',
                'suspension_count': '5',
                'real_raising_limit_count': '34',
                'real_limit_down_count': '1',
            }
        """
        logger.info("获取乐股市场活跃度数据")

        try:
            resp = self.session.get(self.MARKET_ACTIVITY_URL, timeout=15)
            resp.raise_for_status()
            html = resp.text

            return self._parse_market_activity(html)
        except Exception as e:
            logger.error(f"获取乐股市场活跃度失败: {e}")
            raise

    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def fetch_market_congestion(self) -> Optional[str]:
        """
        获取大盘拥挤度数据

        Returns:
            拥挤度字符串，例如：'拥挤度: 43.92%'
        """
        logger.info("获取乐股大盘拥挤度数据")

        try:
            resp = self.session.get(self.MARKET_CONGESTION_URL, timeout=15)
            resp.raise_for_status()
            html = resp.text

            return self._parse_congestion(html)
        except Exception as e:
            logger.error(f"获取乐股大盘拥挤度失败: {e}")
            raise

    # 涨跌分布字段映射 (从 og:description 提取)
    DISTRIBUTION_PATTERNS = {
        'limit_up_count': r'(\d+)家涨停',
        'limit_down_count': r'(\d+)家跌停',
        'up_count': r'(\d+)家上涨',
        'down_count': r'(\d+)家下跌',
        'up_0_3': r'(\d+)家上涨0%~3%',
        'up_3_5': r'(\d+)家上涨3%~5%',
        'up_5_7': r'(\d+)家上涨5%~7%',
        'up_7_10': r'(\d+)家上涨7%~10%',
        'up_10_20': r'(\d+)家上涨10%~20%',
        'down_0_3': r'(\d+)家下跌0%~3%',
        'down_3_5': r'(\d+)家下跌3%~5%',
        'down_5_7': r'(\d+)家下跌5%~7%',
        'down_7_10': r'(\d+)家下跌7%~10%',
        'down_10_20': r'(\d+)家下跌10%~20%',
    }

    def _parse_market_activity(self, html: str) -> Optional[Dict]:
        """解析市场活跃度 HTML (优先从 data-chart 属性提取)"""
        result = {}

        # 方法1: 从 data-chart 属性中提取（最可靠）
        data_chart_fields = {
            'totalUp': 'up_count',
            'totalDown': 'down_count',
            'priceStop': 'flat_count',
            'limitUp': 'limit_up_count',
            'limitDown': 'limit_down_count',
            'pricePaused': 'suspension_count',
            'realLimitUp': 'real_limit_up_count',
            'realLimitDown': 'real_limit_down_count',
            'up0To3': 'up_0_3',
            'up3To5': 'up_3_5',
            'up5To7': 'up_5_7',
            'up7To10': 'up_7_10',
            'up10To20': 'up_10_20',
            'down0To3': 'down_0_3',
            'down3To5': 'down_3_5',
            'down5To7': 'down_5_7',
            'down7To10': 'down_7_10',
            'down10To20': 'down_10_20',
        }
        
        for attr_name, field_name in data_chart_fields.items():
            pattern = rf'id="{attr_name}"[^>]*data-chart=\'(\d+)\''
            match = re.search(pattern, html)
            if match:
                result[field_name] = match.group(1)
        
        if 'up_count' in result and 'down_count' in result:
            logger.info(f"从 data-chart 提取: 上涨{result.get('up_count', '?')}, 下跌{result.get('down_count', '?')}, "
                       f"涨停{result.get('limit_up_count', '?')}, 跌停{result.get('limit_down_count', '?')}, "
                       f"平盘{result.get('flat_count', '?')}, 停牌{result.get('suspension_count', '?')}, "
                       f"真实涨停{result.get('real_limit_up_count', '?')}, 真实跌停{result.get('real_limit_down_count', '?')}")
            return result

        # 方法2: 从 og:description 元数据中提取涨跌分布
        og_desc_pattern = r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"'
        og_match = re.search(og_desc_pattern, html)
        
        if og_match:
            og_content = og_match.group(1)
            logger.info(f"从 og:description 提取涨跌分布数据")
            
            # 从 og:description 提取所有分布字段
            for field, pattern in self.DISTRIBUTION_PATTERNS.items():
                match = re.search(pattern, og_content)
                if match:
                    result[field] = match.group(1)
            
            # 如果成功提取了核心数据
            if 'up_count' in result and 'down_count' in result:
                logger.info(f"乐股市场活跃度: 上涨{result.get('up_count', '?')}, 下跌{result.get('down_count', '?')}, "
                           f"涨停{result.get('limit_up_count', '?')}, 跌停{result.get('limit_down_count', '?')}")
                return result
        
        # 方法3: 回退到从 HTML 表格中提取
        logger.info("回退到从HTML表格提取数据...")
        
        # 匹配涨跌比: 从 h4 标签中提取
        ratio_pattern = r'<h4[^>]*>([^<]*涨跌比[^<]*)</h4>'
        ratio_match = re.search(ratio_pattern, html)
        if ratio_match:
            result['rise_fall_ratio'] = ratio_match.group(1).strip()

        # 提取表格中的颜色标记的数值
        red_pattern = r'class="color-red"[^>]*>(\d+)'
        green_pattern = r'class="color-green"[^>]*>(\d+)'
        gray_pattern = r'class="color-gray"[^>]*>(\d+)'
        
        red_matches = re.findall(red_pattern, html)
        green_matches = re.findall(green_pattern, html)
        gray_matches = re.findall(gray_pattern, html)

        if len(red_matches) >= 3 and len(green_matches) >= 3 and len(gray_matches) >= 1:
            result['up_count'] = red_matches[0]
            result['down_count'] = green_matches[0]
            result['flat_count'] = gray_matches[0]
            result['limit_up_count'] = red_matches[1]
            result['limit_down_count'] = green_matches[1]
            result['suspension_count'] = gray_matches[1]
            result['real_limit_up_count'] = red_matches[2]
            result['real_limit_down_count'] = green_matches[2]

            logger.info(f"乐股市场活跃度(表格): 上涨{result['up_count']}, 下跌{result['down_count']}, "
                       f"涨停{result['limit_up_count']}, 跌停{result['limit_down_count']}")
            return result
        else:
            logger.warning(f"乐股市场活跃度解析失败: red={len(red_matches)}, green={len(green_matches)}, gray={len(gray_matches)}")
            return None

    def _parse_congestion(self, html: str) -> Optional[str]:
        """解析大盘拥挤度 HTML"""
        # 匹配 div.data-view-head-ashares-congestion 的内容
        pattern = r'class="data-view-head-ashares-congestion"[^>]*>([^<]+)'
        match = re.search(pattern, html)
        
        if match:
            congestion = match.group(1).strip()
            logger.info(f"乐股大盘拥挤度: {congestion}")
            return congestion
        else:
            logger.warning("乐股大盘拥挤度解析失败")
            return None

    def get_all_market_data(self) -> Optional[Dict]:
        """
        获取所有市场数据（活跃度 + 拥挤度）
        
        Returns:
            完整的市场数据字典
        """
        try:
            activity = self.fetch_market_activity()
            congestion_str = self.fetch_market_congestion()

            if activity is None:
                return None

            if congestion_str:
                activity['congestion'] = congestion_str

            return activity
        except Exception as e:
            logger.error(f"获取乐股市场数据失败: {e}")
            return None