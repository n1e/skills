#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺个股点评和资讯采集器
用于获取个股的详细信息、点评和相关资讯
"""

import json
import re
import time
from typing import List, Dict, Any, Optional

import requests

from logger import logger
from utils.retry import retry_with_backoff


class HexinStockAnalyzer:
    """
    同花顺个股分析器
    用于获取个股点评、资讯和详细信息
    """
    
    def __init__(self):
        """初始化同花顺个股分析器"""
        self.session = requests.Session()
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://stockpage.10jqka.com.cn',
            'Referer': 'https://stockpage.10jqka.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    
    def _format_stock_code(self, code: str) -> str:
        """
        格式化股票代码
        
        Args:
            code: 原始股票代码
            
        Returns:
            格式化后的股票代码（6位数字）
        """
        code = str(code).strip()
        # 去掉可能的前缀
        if '.' in code:
            code = code.split('.')[0]
        # 确保6位
        if len(code) == 6 and code.isdigit():
            return code
        # 尝试提取6位数字
        match = re.search(r'(\d{6})', code)
        if match:
            return match.group(1)
        return code
    
    def _get_market_prefix(self, code: str) -> str:
        """
        根据股票代码获取市场前缀
        
        Args:
            code: 6位股票代码
            
        Returns:
            市场前缀: 'sh' 或 'sz'
        """
        code = self._format_stock_code(code)
        if code.startswith('6'):
            return 'sh'
        elif code.startswith(('0', '3')):
            return 'sz'
        return 'sz'  # 默认深交所
    
    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def get_stock_basic_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息（实时行情）
        
        Args:
            code: 股票代码
            
        Returns:
            股票基本信息字典，包含名称、最新价、涨跌幅等
        """
        code = self._format_stock_code(code)
        logger.info(f"获取股票基本信息: {code}")
        
        # 使用同花顺个股页面接口
        url = f"https://stockpage.10jqka.com.cn/{code}/"
        
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            html = resp.text
            
            # 从HTML中提取股票名称
            name_match = re.search(r'<title>([^|]+)\|', html)
            name = name_match.group(1).strip() if name_match else ''
            
            # 提取最新价
            price_match = re.search(r'最新价[：:]\s*([\d.]+)', html)
            latest_price = float(price_match.group(1)) if price_match else 0.0
            
            # 提取涨跌幅
            change_match = re.search(r'涨跌幅[：:]\s*([+-]?[\d.]+)%', html)
            change_pct = float(change_match.group(1)) if change_match else 0.0
            
            # 尝试从script标签提取更详细的数据
            script_match = re.search(r'var\s+stockinfo\s*=\s*({[^}]+})', html)
            if script_match:
                try:
                    stockinfo = json.loads(script_match.group(1))
                    name = stockinfo.get('name', name)
                    latest_price = float(stockinfo.get('price', latest_price))
                    change_pct = float(stockinfo.get('changepercent', change_pct))
                except (json.JSONDecodeError, ValueError):
                    pass
            
            result = {
                'code': code,
                'name': name,
                'latest_price': latest_price,
                'change_pct': change_pct,
            }
            
            logger.info(f"股票基本信息获取成功: {name}({code}) 最新价={latest_price} 涨跌幅={change_pct}%")
            return result
            
        except Exception as e:
            logger.error(f"获取股票基本信息失败 {code}: {e}")
            return None
    
    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def get_stock_comment(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票点评（同花顺个股分析）
        
        Args:
            code: 股票代码
            
        Returns:
            点评数据字典，包含技术面、基本面、消息面分析
        """
        code = self._format_stock_code(code)
        logger.info(f"获取股票点评: {code}")
        
        # 尝试多个可能的接口
        try:
            # 接口1: 同花顺个股诊断
            url = f"https://stockpage.10jqka.com.cn/analysis/{code}/"
            resp = self.session.get(url, headers=self.headers, timeout=15)
            html = resp.text
            
            # 提取点评信息
            comment = {
                'technical_analysis': '',
                'fundamental_analysis': '',
                'news_analysis': '',
                'overall_rating': '',
                'summary': ''
            }
            
            # 技术面分析
            tech_match = re.search(r'技术面分析[：:]\s*([^<\n]+)', html)
            if tech_match:
                comment['technical_analysis'] = tech_match.group(1).strip()
            
            # 基本面分析
            fund_match = re.search(r'基本面分析[：:]\s*([^<\n]+)', html)
            if fund_match:
                comment['fundamental_analysis'] = fund_match.group(1).strip()
            
            # 消息面分析
            news_match = re.search(r'消息面分析[：:]\s*([^<\n]+)', html)
            if news_match:
                comment['news_analysis'] = news_match.group(1).strip()
            
            # 综合评级
            rating_match = re.search(r'综合评级[：:]\s*([^<\n]+)', html)
            if rating_match:
                comment['overall_rating'] = rating_match.group(1).strip()
            
            # 尝试从诊断摘要提取
            summary_match = re.search(r'诊断摘要[：:]\s*([^<\n]+)', html)
            if summary_match:
                comment['summary'] = summary_match.group(1).strip()
            
            # 如果上面的方式没有获取到数据，尝试从script标签提取
            if not any(comment.values()):
                script_match = re.search(r'var\s+analysis\s*=\s*({[^}]+})', html)
                if script_match:
                    try:
                        analysis_data = json.loads(script_match.group(1))
                        comment['technical_analysis'] = analysis_data.get('technical', '')
                        comment['fundamental_analysis'] = analysis_data.get('fundamental', '')
                        comment['news_analysis'] = analysis_data.get('news', '')
                        comment['overall_rating'] = analysis_data.get('rating', '')
                        comment['summary'] = analysis_data.get('summary', '')
                    except json.JSONDecodeError:
                        pass
            
            logger.info(f"股票点评获取成功: {code}")
            return comment
            
        except Exception as e:
            logger.error(f"获取股票点评失败 {code}: {e}")
            return None
    
    @retry_with_backoff(initial_delay=1.0, max_delay=5.0, max_attempts=3)
    def get_stock_news(self, code: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        获取股票相关资讯
        
        Args:
            code: 股票代码
            count: 获取资讯数量
            
        Returns:
            资讯列表，每项包含标题、来源、时间、链接等
        """
        code = self._format_stock_code(code)
        logger.info(f"获取股票资讯: {code}")
        
        news_list = []
        
        try:
            # 接口: 同花顺个股资讯
            url = f"https://stockpage.10jqka.com.cn/news/{code}/"
            resp = self.session.get(url, headers=self.headers, timeout=15)
            html = resp.text
            
            # 解析资讯列表
            # 匹配类似: <a href="..." target="_blank">标题</a>
            pattern = r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>([^<]*)</a>'
            matches = re.findall(pattern, html)
            
            for link, title in matches[:count]:
                title = title.strip()
                if not title or len(title) < 5:
                    continue
                
                # 处理链接
                if link.startswith('//'):
                    link = 'https:' + link
                elif not link.startswith('http'):
                    link = f"https://stockpage.10jqka.com.cn{link}"
                
                news_list.append({
                    'title': title,
                    'url': link,
                    'source': '同花顺',
                    'publish_time': '',
                    'summary': ''
                })
            
            # 尝试从JSON数据获取更详细的资讯
            json_pattern = r'var\s+newsList\s*=\s*(\[[^\]]+\])'
            json_match = re.search(json_pattern, html)
            if json_match:
                try:
                    news_data = json.loads(json_match.group(1))
                    news_list = []
                    for item in news_data[:count]:
                        news_list.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', item.get('link', '')),
                            'source': item.get('source', '同花顺'),
                            'publish_time': item.get('time', item.get('publish_time', '')),
                            'summary': item.get('summary', item.get('digest', ''))
                        })
                except json.JSONDecodeError:
                    pass
            
            logger.info(f"股票资讯获取成功: {code}, 共{len(news_list)}条")
            return news_list
            
        except Exception as e:
            logger.error(f"获取股票资讯失败 {code}: {e}")
            return []
    
    def get_stock_full_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票完整详情（包含基本信息、点评和资讯）
        
        Args:
            code: 股票代码
            
        Returns:
            完整详情字典
        """
        code = self._format_stock_code(code)
        logger.info(f"获取股票完整详情: {code}")
        
        # 并行获取各项数据
        basic_info = self.get_stock_basic_info(code)
        comment = self.get_stock_comment(code)
        news = self.get_stock_news(code, count=10)
        
        if not basic_info:
            logger.warning(f"无法获取股票基本信息: {code}")
            return None
        
        result = {
            'code': basic_info.get('code', code),
            'name': basic_info.get('name', ''),
            'latest_price': basic_info.get('latest_price', 0.0),
            'change_pct': basic_info.get('change_pct', 0.0),
            'comment': comment or {
                'technical_analysis': '',
                'fundamental_analysis': '',
                'news_analysis': '',
                'overall_rating': '',
                'summary': ''
            },
            'news': news or []
        }
        
        return result


# 便捷函数
def get_stock_detail(code: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取股票详情
    
    Args:
        code: 股票代码
        
    Returns:
        股票详情字典
    """
    analyzer = HexinStockAnalyzer()
    return analyzer.get_stock_full_detail(code)
