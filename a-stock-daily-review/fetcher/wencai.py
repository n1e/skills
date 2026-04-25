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
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

from logger import logger
from utils.retry import retry_with_backoff
from utils.helpers import rand_string
from models.market import MarketData, VolumeData
from models.stock import SurgeStock


def find_hexin_v_js() -> str:
    """查找hexin_v.js路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 向上找3层到项目根目录
    for _ in range(4):
        script_dir = os.path.dirname(script_dir)
    
    js_path = os.path.join(script_dir, 'lib', 'hexin_v.js')
    if os.path.exists(js_path):
        return js_path
    
    # 尝试相对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(current_dir, '..', '..', 'lib', 'hexin_v.js')
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
    
    def get_market_data(self) -> MarketData:
        """获取大盘数据"""
        logger.info("开始获取大盘数据")
        self._init_session()
        
        market = MarketData()
        market.date = datetime.now().strftime('%Y-%m-%d')
        
        # 查询涨跌统计
        try:
            result = self.query("今日沪深A股涨跌统计")
            datas = self._parse_answer(result)
            if datas:
                item = datas[0]
                market.up_count = int(item.get('上涨家数', item.get('上涨', 0)))
                market.down_count = int(item.get('下跌家数', item.get('下跌', 0)))
                market.flat_count = int(item.get('平盘家数', item.get('平盘', 0)))
                market.total_count = market.up_count + market.down_count + market.flat_count
                logger.info(f"涨跌统计: 上涨{market.up_count}, 下跌{market.down_count}, 平盘{market.flat_count}")
        except Exception as e:
            logger.error(f"涨跌统计查询失败: {e}")
        
        # 查询涨跌停数量
        try:
            result = self.query("今日沪深A股涨跌停数量")
            datas = self._parse_answer(result)
            if datas:
                item = datas[0]
                market.limit_up_count = int(item.get('涨停家数', item.get('涨停', 0)))
                market.limit_down_count = int(item.get('跌停家数', item.get('跌停', 0)))
                logger.info(f"涨跌停: 涨停{market.limit_up_count}, 跌停{market.limit_down_count}")
        except Exception as e:
            logger.error(f"涨跌停查询失败: {e}")
        
        # 查询真实涨跌停（非一字板）
        try:
            result = self.query("今日非一字涨停股票")
            datas = self._parse_answer(result)
            if datas:
                market.real_limit_up_count = len(datas)
                logger.info(f"非一字涨停: {market.real_limit_up_count}")
        except Exception as e:
            logger.error(f"非一字涨停查询失败: {e}")
        
        try:
            result = self.query("今日非一字跌停股票")
            datas = self._parse_answer(result)
            if datas:
                market.real_limit_down_count = len(datas)
                logger.info(f"非一字跌停: {market.real_limit_down_count}")
        except Exception as e:
            logger.error(f"非一字跌停查询失败: {e}")
        
        # 查询停牌家数
        try:
            result = self.query("今日沪深A股停牌家数")
            datas = self._parse_answer(result)
            if datas:
                item = datas[0]
                market.suspension_count = int(item.get('停牌家数', item.get('停牌', 0)))
                logger.info(f"停牌家数: {market.suspension_count}")
        except Exception as e:
            logger.error(f"停牌家数查询失败: {e}")
        
        # 查询成交量
        try:
            result = self.query("今日沪深两市总成交量")
            datas = self._parse_answer(result)
            if datas:
                item = datas[0]
                vol = item.get('总成交量', item.get('成交量', '0'))
                if isinstance(vol, str):
                    vol = vol.replace(',', '')
                market.total_volume = float(vol)
                logger.info(f"总成交量: {market.total_volume:,.0f}手")
        except Exception as e:
            logger.error(f"成交量查询失败: {e}")
        
        return market
    
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
    
    def analyze_surge_reason(self, reason: str) -> str:
        """分析涨停原因分类"""
        if not reason:
            return "其他"
        
        reason_lower = reason.lower()
        
        # 业绩相关
        if any(kw in reason_lower for kw in ['业绩', '增长', '利润', '预增', '扭亏', '盈利']):
            return "业绩预增"
        
        # 并购重组
        if any(kw in reason_lower for kw in ['重组', '并购', '收购', '借壳', '股权', '转让']):
            return "并购重组"
        
        # 政策利好
        if any(kw in reason_lower for kw in ['政策', '补贴', '扶持', '规划', '利好', '新基建']):
            return "政策利好"
        
        # 热点概念
        if any(kw in reason_lower for kw in ['概念', '题材', '风口', 'ai', '人工智能', '新能源', '芯片']):
            return "概念炒作"
        
        # 资金流入
        if any(kw in reason_lower for kw in ['资金', '主力', '大单', '流入', '抢筹']):
            return "资金推动"
        
        # 技术突破
        if any(kw in reason_lower for kw in ['突破', '创新高', '新高', '启动', '爆发']):
            return "技术突破"
        
        # 行业景气
        if any(kw in reason_lower for kw in ['行业', '景气', '复苏', '供需', '涨价']):
            return "行业景气"
        
        # 产品/订单
        if any(kw in reason_lower for kw in ['订单', '产品', '签约', '中标', '合同']):
            return "新产品/订单"
        
        # 股权激励
        if any(kw in reason_lower for kw in ['激励', '回购', '增持', '员工持股']):
            return "股权激励"
        
        # 高送转
        if any(kw in reason_lower for kw in ['送转', '分红', '高送', '派息']):
            return "高送转预期"
        
        return "其他"
    
    def get_heat_rank(self, top: int = 50) -> List:
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
                        ranks.append({
                            'code': code_str,
                            'name': str(name),
                            'rank': i + 1,
                            'heat_score': top - i,
                            'source': 'wencai'
                        })
            
            logger.info(f"问财获取到 {len(ranks)} 只股票")
        except Exception as e:
            logger.error(f"问财人气排名获取失败: {e}")
        
        return ranks