#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问财数据采集器
用于获取大盘数据、涨停股票、成交量历史等
参考: skills/stock-heat-rank-py/main.py 中的实现
"""

import os
import re
import subprocess
import sys
import time
import urllib.parse
from typing import List, Dict, Any, Optional

import requests

from logger import logger
from utils.retry import retry_with_backoff
from utils.helpers import rand_string
from models.market import VolumeData
from models.stock import SurgeStock, HeatRank


def _find_project_root() -> str:
    """从当前文件向上查找项目根目录（以 SKILL.md 为标识）"""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.exists(os.path.join(current, 'SKILL.md')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.dirname(os.path.abspath(__file__))


def find_hexin_v_js() -> str:
    """查找hexin_v.js路径"""
    root = _find_project_root()
    js_path = os.path.join(root, 'lib', 'hexin_v.js')
    if os.path.exists(js_path):
        return js_path
    return 'lib/hexin_v.js'


class WencaiFetcher:
    """问财数据采集器 - 参考stock-heat-rank-py实现"""
    
    def __init__(self):
        self.session = requests.Session()
        self.other_uid = f"Ths_iwencai_Xuangu_{rand_string(32)}"
        self.cookies = {
            'other_uid': self.other_uid,
            'ta_random_userid': rand_string(10),
            'v': ''
        }
        self.js_path = find_hexin_v_js()
    
    def _generate_hexin_v(self) -> str:
        """生成Hexin-V签名"""
        timestamp = f"{time.time():.3f}"
        try:
            result = subprocess.run(
                ['node', self.js_path, timestamp],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"生成Hexin-V失败: {e}")
            return "default_hexin_v_value"
    
    def _visit_main(self):
        """访问主页获取初始cookies"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        try:
            resp = self.session.get('https://www.iwencai.com', headers=headers, timeout=15)
            for cookie in resp.cookies:
                self.cookies[cookie.name] = cookie.value
        except Exception:
            pass
    
    def _visit_search(self):
        """访问搜索页"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.iwencai.com',
        }
        try:
            resp = self.session.get('https://www.iwencai.com/unifiedwap/home/index', headers=headers, timeout=15)
            for cookie in resp.cookies:
                self.cookies[cookie.name] = cookie.value
        except Exception:
            pass
    
    def _visit_hint(self):
        """初始化会话"""
        hexin_v = self._generate_hexin_v()
        # 更新cookies中的v值为hexin_v
        self.cookies['v'] = hexin_v
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.iwencai.com',
            'Referer': 'https://www.iwencai.com/unifiedwap/home/index',
            'Hexin-V': hexin_v,
        }
        data = {
            'dataType': 'history',
            'isAll': '1',
            'num': '20',
            'queryType': 'index',
            'relatedId': '',
        }
        try:
            resp = self.session.post(
                'https://www.iwencai.com/unifiedwap/suggest/V1/index/query-hint-list',
                headers=headers,
                data=data,
                cookies=self.cookies,
                timeout=15
            )
        except Exception:
            pass
    
    def _init_session(self):
        """初始化问财会话（参考stock-heat-rank-py实现）"""
        logger.info("→ 访问问财主页...")
        self._visit_main()
        time.sleep(0.3)
        
        logger.info("→ 访问搜索页...")
        self._visit_search()
        time.sleep(0.3)
        
        logger.info("→ 初始化会话...")
        self._visit_hint()
        time.sleep(0.3)
    
    def query(self, question: str, perpage: int = 10) -> dict:
        """执行问财查询"""
        hexin_v = self._generate_hexin_v()
        # 更新cookies中的v值为hexin_v
        self.cookies['v'] = hexin_v
        
        payload = {
            "source": "Ths_iwencai_Xuangu",
            "version": "2.0",
            "query_area": "",
            "block_list": "",
            "add_info": '{"urp":{"scene":1,"company":1,"business":1},"contentType":"json","searchInfo":true}',
            "question": question,
            "perpage": perpage,
            "page": 1,
            "secondary_intent": "",
            "log_info": '{"input_type":"typewrite"}',
            "rsh": self.other_uid,
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.iwencai.com',
            'Referer': f'https://www.iwencai.com/unifiedwap/result?w={urllib.parse.quote(question)}',
            'Hexin-V': hexin_v,
        }
        
        resp = self.session.post(
            'https://www.iwencai.com/customized/chart/get-robot-data',
            headers=headers,
            json=payload,
            cookies=self.cookies,
            timeout=30
        )
        return resp.json()
    
    def _parse_answer(self, data: dict) -> List[dict]:
        """解析问财返回数据"""
        status = data.get('errno', data.get('status_code', -1))
        if status != 0:
            logger.warning(f"问财返回错误码: {status}")
            return []
        
        try:
            answer = data.get('data', {}).get('answer', [])
            if not answer:
                return []
            
            txt_list = answer[0].get('txt', [])
            if not txt_list:
                return []
            
            # txt_list可能是列表或直接包含content
            if isinstance(txt_list, list) and len(txt_list) > 0:
                first_item = txt_list[0]
                # 如果是字符串列表，直接返回
                if isinstance(first_item, str):
                    return [{'result': first_item}]
                # 如果是字典，检查是否有content
                if isinstance(first_item, dict):
                    if 'content' in first_item:
                        content = first_item.get('content', {})
                    else:
                        # 直接是数据
                        return txt_list
                    
                    components = content.get('components', [])
                    if not components:
                        return []
                    
                    # 组件可能是列表或直接包含data
                    first_component = components[0]
                    if 'data' in first_component:
                        comp_data = first_component.get('data', {})
                        if isinstance(comp_data, dict):
                            return comp_data.get('datas', [])
                        elif isinstance(comp_data, list):
                            return comp_data
                    elif 'datas' in first_component:
                        return first_component.get('datas', [])
                return []
            return []
        except Exception as e:
            logger.error(f"解析问财数据失败: {e}")
            return []
    
    def get_volume_history(self, days: int = 30) -> List[VolumeData]:
        """获取指定天数的成交额历史（使用A股总成交金额，单位：元）"""
        logger.info(f"获取最近{days}日成交额历史")
        volumes = []
        
        try:
            # 初始化会话
            self._init_session()
            
            # 使用用户提供的查询语句
            result = self.query(f"A股总成交金额 最近{days}个交易日", perpage=days)
            
            # 直接从返回数据中提取
            try:
                answer = result.get('data', {}).get('answer', [])
                if answer and len(answer) > 0:
                    txt_list = answer[0].get('txt', [])
                    if txt_list and isinstance(txt_list, list) and len(txt_list) > 0:
                        first_item = txt_list[0]
                        if isinstance(first_item, dict):
                            content = first_item.get('content', {})
                            if isinstance(content, dict):
                                components = content.get('components', [])
                                if isinstance(components, list):
                                    for comp in components:
                                        if isinstance(comp, dict):
                                            comp_data = comp.get('data', {})
                                            if isinstance(comp_data, dict):
                                                datas = comp_data.get('datas', [])
                                                if isinstance(datas, list) and len(datas) > 0:
                                                    # 遍历所有数据项
                                                    for item in datas:
                                                        if isinstance(item, dict):
                                                            # 提取日期和成交额
                                                            date_str = item.get('时间区间', item.get('date', ''))
                                                            amount = item.get('成交额', item.get('A股总成交金额', item.get('amount', 0)))
                                                            
                                                            if date_str and amount:
                                                                # 格式化日期（date_str可能是int类型如20250407）
                                                                date_str = str(date_str)
                                                                if len(date_str) == 8:
                                                                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                                                
                                                                # 解析成交额（可能是字符串如"1.23万亿"）
                                                                if isinstance(amount, str):
                                                                    if '万亿' in amount:
                                                                        amount = float(amount.replace('万亿', '')) * 1000000000000
                                                                    elif '亿' in amount:
                                                                        amount = float(amount.replace('亿', '')) * 100000000
                                                                    elif '万' in amount:
                                                                        amount = float(amount.replace('万', '')) * 10000
                                                                    else:
                                                                        amount = float(amount.replace(',', ''))
                                                                
                                                                volumes.append(VolumeData(
                                                                    date=str(date_str),
                                                                    volume=float(amount)
                                                                ))
                                                                logger.info(f"提取到 {date_str}: {amount:,.0f}元")
            except Exception as e:
                import traceback
                logger.warning(f"解析成交额数据失败: {e}")
                logger.warning(traceback.format_exc())
            
            logger.info(f"获取到 {len(volumes)} 日成交额数据")
        except Exception as e:
            logger.error(f"成交额历史查询失败: {e}")
        
        return volumes
    
    def get_surge_stocks(self, min_change: float = 9.5, max_stocks: int = 200) -> List[SurgeStock]:
        """获取涨停股票列表"""
        logger.info(f"获取涨停股票（最低涨幅{min_change}%）")
        stocks = []
        
        try:
            result = self.query(f"今日涨停股", perpage=max_stocks)
            datas = self._parse_answer(result)
            
            for item in datas:
                # 兼容多种字段名称
                code = item.get('股票代码', item.get('code', ''))
                name = item.get('股票简称', item.get('名称', ''))
                price = item.get('最新价', item.get('收盘价', 0))
                change_pct = item.get('最新涨跌幅', item.get('涨跌幅', item.get('涨幅', 0)))
                
                # 涨停原因（兼容多种字段名）
                reason = item.get('涨停原因类别', item.get('涨停原因', item.get('涨停理由', '')))
                # 处理带日期的字段名如 "涨停原因类别[20260403]"
                if not reason:
                    for key in item:
                        if '涨停原因' in key or '涨停理由' in key:
                            reason = item[key]
                            break
                
                # 标准化代码
                code_str = str(code)
                if '.' in code_str:
                    code_str = code_str.split('.')[0]
                
                try:
                    change_val = float(change_pct) if change_pct else 0
                except (ValueError, TypeError):
                    change_val = 0
                
                if code_str and change_val >= min_change:
                    stocks.append(SurgeStock(
                        code=code_str,
                        name=str(name) if name else '',
                        price=float(price) if price else 0,
                        change_pct=change_val,
                        reason=str(reason) if reason else ''
                    ))
            
            logger.info(f"获取到 {len(stocks)} 只涨停股")
        except Exception as e:
            logger.error(f"涨停股票查询失败: {e}")
        
        return stocks
    
    def get_heat_rank(self, top: int = 50) -> List[HeatRank]:
        """获取问财人气排名（参考stock-heat-rank-py实现）"""
        logger.info(f"获取问财人气排名TOP{top}")
        
        # 初始化会话
        self._init_session()
        
        ranks = []
        
        try:
            result = self.query(f"人气排名前{top}", perpage=top)
            datas = self._parse_answer(result)
            
            for i, item in enumerate(datas[:top]):
                code = item.get('股票代码', item.get('code', ''))
                name = item.get('股票简称', item.get('name', ''))
                if code and name:
                    # 标准化股票代码，去掉.SZ/.SH后缀
                    code_str = str(code)
                    if '.' in code_str:
                        code_str = code_str.split('.')[0]
                    # 只保留6位数字代码
                    if len(code_str) == 6 and code_str.isdigit():
                        ranks.append(HeatRank(
                            code=code_str,
                            name=str(name),
                            rank=i + 1,
                            heat_score=top - i,
                            source='wencai'
                        ))
            
            logger.info(f"问财获取到 {len(ranks)} 只股票")
        except Exception as e:
            logger.error(f"问财人气排名获取失败: {e}")
        
        return ranks