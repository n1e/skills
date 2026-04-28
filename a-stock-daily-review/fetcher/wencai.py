#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问财数据采集器

仅使用官方 OpenAPI (https://openapi.iwencai.com/v1/query2data) 进行数据查询
旧 URL 方式和 CLI 方式已移除，因为接口已过期

需要配置 IWENCAI_API_KEY 环境变量或在 config.json 中配置
"""

import json
import os
import re
import sys
from typing import List, Dict, Any, Optional

import requests

from logger import logger
from models.market import VolumeData
from models.stock import SurgeStock, HeatRank

try:
    from config import config as global_config
except ImportError:
    global_config = None


def get_wencai_config() -> Dict[str, Any]:
    """获取问财配置
    
    优先从环境变量读取，然后从 config.json 读取
    """
    config_dict = {
        'api_key': '',
        'skill_name': '基本资料查询',
    }
    
    env_api_key = os.environ.get('IWENCAI_API_KEY', '')
    if env_api_key:
        config_dict['api_key'] = env_api_key
    
    if global_config:
        json_api_key = global_config.get('wencai.api_key', '')
        if json_api_key and not config_dict['api_key']:
            config_dict['api_key'] = json_api_key
        
        skill_name = global_config.get('wencai.skill_name', '')
        if skill_name:
            config_dict['skill_name'] = skill_name
    
    return config_dict


def check_api_key_configured() -> bool:
    """检查 API Key 是否已配置
    
    Returns:
        True 如果已配置，False 否则
    """
    config_dict = get_wencai_config()
    api_key = config_dict.get('api_key', '')
    if not api_key:
        return False
    if api_key == 'sk-proj-00':
        return False
    return True


def get_api_key_reminder() -> str:
    """获取 API Key 配置提醒信息"""
    return """
⚠️  问财 API Key 未配置！

需要配置 IWENCAI_API_KEY 环境变量才能使用问财数据查询功能。

配置方式：
1. 环境变量方式：
   Windows: set IWENCAI_API_KEY=your_api_key_here
   Linux/Mac: export IWENCAI_API_KEY=your_api_key_here

2. 或在 config.json 中配置：
   "wencai": {
     "api_key": "your_api_key_here",
     ...
   }

获取 API Key：请访问同花顺问财开放平台申请
"""


class WencaiOpenAPIError(Exception):
    """OpenAPI 错误异常类"""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class WencaiOpenAPI:
    """
    问财官方 OpenAPI 客户端
    
    使用 https://openapi.iwencai.com/v1/query2data 进行数据查询
    这是当前唯一支持的方式
    
    参考：基本资料查询 skill 中的实现
    """
    
    DEFAULT_API_URL = "https://openapi.iwencai.com/v1/query2data"
    DEFAULT_PAGE = "1"
    DEFAULT_LIMIT = "10"
    DEFAULT_IS_CACHE = "1"
    DEFAULT_EXPAND_INDEX = "true"
    
    def __init__(self):
        self._config = get_wencai_config()
        self._api_key = self._config.get('api_key', '')
        self._available = None
    
    def _check_available(self) -> bool:
        """检查 OpenAPI 是否可用"""
        if self._available is not None:
            return self._available
        
        if not self._api_key:
            logger.warning("IWENCAI_API_KEY 未配置，OpenAPI 不可用")
            self._available = False
            return False
        
        if self._api_key == 'sk-proj-00':
            logger.warning("IWENCAI_API_KEY 使用默认占位值，请配置真实的 API Key")
            self._available = False
            return False
        
        self._available = True
        logger.info("问财 OpenAPI 可用")
        return self._available
    
    def query(self, query: str, page: str = None, limit: str = None) -> Optional[Dict]:
        """
        使用 OpenAPI 执行查询
        
        Args:
            query: 查询字符串
            page: 分页参数
            limit: 每页条数
            
        Returns:
            包含 datas、code_count、chunks_info 等字段的字典，失败返回 None
        """
        if not self._check_available():
            logger.error(f"OpenAPI 不可用，无法执行查询: {query}")
            return None
        
        page = page or self.DEFAULT_PAGE
        limit = limit or self.DEFAULT_LIMIT
        
        payload = {
            "query": query,
            "page": page,
            "limit": limit,
            "is_cache": self.DEFAULT_IS_CACHE,
            "expand_index": self.DEFAULT_EXPAND_INDEX
        }
        
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"使用问财 OpenAPI 查询: {query} (page={page}, limit={limit})")
            
            resp = requests.post(
                self.DEFAULT_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            result = resp.json()
            
            if isinstance(result, dict):
                status_code = result.get("status_code", 0)
                if status_code != 0:
                    status_msg = result.get("status_msg", "未知错误")
                    logger.warning(f"OpenAPI 返回错误: status_code={status_code}, msg={status_msg}")
                    return None
                
                return {
                    "datas": result.get("datas", []),
                    "code_count": result.get("code_count", 0),
                    "chunks_info": result.get("chunks_info", {}),
                    "status_code": 0
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"OpenAPI 请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"OpenAPI 响应解析失败: {e}")
            return None
        except Exception as e:
            logger.warning(f"OpenAPI 查询异常: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查 OpenAPI 是否完全可用"""
        return self._check_available()


class WencaiFetcher:
    """
    问财数据采集器
    
    仅使用 OpenAPI 方式进行数据查询
    旧 URL 方式和 CLI 方式已移除
    """
    
    def __init__(self):
        self._config = get_wencai_config()
        self._skill_name = self._config.get('skill_name', '基本资料查询')
        
        self._openapi = WencaiOpenAPI()
    
    def query(self, question: str, perpage: int = 100) -> dict:
        """
        执行问财查询
        
        仅使用 OpenAPI 方式
        
        Args:
            question: 查询问题
            perpage: 每页条数
            
        Returns:
            查询结果字典，如果 API 不可用返回空字典
        """
        if self._openapi.is_available():
            result = self._openapi.query(question, limit=str(perpage))
            if result:
                return self._convert_openapi_result(result)
        
        logger.warning(f"问财查询失败: API 不可用或查询失败，问题: {question}")
        return {}
    
    def _convert_openapi_result(self, openapi_result: Dict) -> Dict:
        """
        将 OpenAPI 返回结果转换为标准格式
        
        OpenAPI 返回格式：
        {
            "datas": [...],
            "code_count": N,
            "chunks_info": {},
            "status_code": 0
        }
        
        标准格式：
        {
            "errno": 0,
            "data": {
                "answer": [
                    {
                        "txt": [
                            {
                                "content": {
                                    "components": [
                                        {
                                            "data": {
                                                "datas": [...]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }
        """
        datas = openapi_result.get('datas', [])
        
        return {
            "errno": 0,
            "status_code": 0,
            "data": {
                "answer": [
                    {
                        "txt": [
                            {
                                "content": {
                                    "components": [
                                        {
                                            "data": {
                                                "datas": datas
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }
    
    def _parse_answer(self, data: dict) -> List[dict]:
        """解析问财返回数据"""
        if not data:
            return []
        
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
            
            if isinstance(txt_list, list) and len(txt_list) > 0:
                first_item = txt_list[0]
                if isinstance(first_item, str):
                    return [{'result': first_item}]
                if isinstance(first_item, dict):
                    if 'content' in first_item:
                        content = first_item.get('content', {})
                    else:
                        return txt_list
                    
                    components = content.get('components', [])
                    if not components:
                        return []
                    
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
        """获取指定天数的成交额历史（使用A股总成交金额，单位：元）
        
        注意：OpenAPI 返回的数据格式是单条记录中包含多个日期的成交额字段，
        字段名格式为：成交额[YYYYMMDD]
        """
        logger.info(f"获取最近{days}日成交额历史")
        volumes = []
        
        if not self._openapi.is_available():
            logger.warning("问财 OpenAPI 不可用，无法获取成交额历史")
            return volumes
        
        try:
            result = self.query(f"同花顺全A 日成交额 最近{days}日", perpage=days)
            
            if isinstance(result, dict):
                captcha_url = result.get('data', {}).get('captcha_url')
                if captcha_url:
                    logger.warning("问财 API 返回验证码要求，数据获取失败")
                    return []
            
            datas = self._parse_answer(result)
            
            date_field_pattern = re.compile(r'成交额\[(\d{8})\]')
            
            for item in datas:
                has_date_in_fields = False
                for key, value in item.items():
                    match = date_field_pattern.match(key)
                    if match:
                        has_date_in_fields = True
                        date_str = match.group(1)
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        
                        if isinstance(value, (int, float)):
                            amount = float(value)
                        elif isinstance(value, str):
                            if '万亿' in value:
                                amount = float(value.replace('万亿', '')) * 1000000000000
                            elif '亿' in value:
                                amount = float(value.replace('亿', '')) * 100000000
                            elif '万' in value:
                                amount = float(value.replace('万', '')) * 10000
                            else:
                                try:
                                    amount = float(value.replace(',', ''))
                                except ValueError:
                                    continue
                        else:
                            try:
                                amount = float(value)
                            except (ValueError, TypeError):
                                continue
                        
                        if amount > 0:
                            volumes.append(VolumeData(
                                date=formatted_date,
                                volume=amount
                            ))
                            logger.info(f"提取到 {formatted_date}: {amount:,.0f}元")
                
                if not has_date_in_fields:
                    date_str = item.get('时间区间', item.get('date', ''))
                    amount = item.get('成交额', item.get('同花顺全A成交金额', item.get('amount', 0)))
                    
                    if date_str and amount:
                        date_str = str(date_str)
                        if len(date_str) == 8:
                            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        
                        if isinstance(amount, str):
                            if '万亿' in amount:
                                amount = float(amount.replace('万亿', '')) * 1000000000000
                            elif '亿' in amount:
                                amount = float(amount.replace('亿', '')) * 100000000
                            elif '万' in amount:
                                amount = float(amount.replace('万', '')) * 10000
                            else:
                                try:
                                    amount = float(amount.replace(',', ''))
                                except ValueError:
                                    continue
                        
                        volumes.append(VolumeData(
                            date=str(date_str),
                            volume=float(amount)
                        ))
                        logger.info(f"提取到 {date_str}: {float(amount):,.0f}元")
            
            volumes.sort(key=lambda x: x.date, reverse=True)
            volumes = volumes[:days]
            
            logger.info(f"获取到 {len(volumes)} 日成交额数据")
        except Exception as e:
            logger.error(f"成交额历史查询失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return volumes
    
    def get_surge_stocks(self, min_change: float = 9.5, max_stocks: int = 200) -> List[SurgeStock]:
        """获取涨停股票列表"""
        logger.info(f"获取涨停股票（最低涨幅{min_change}%）")
        stocks = []
        
        if not self._openapi.is_available():
            logger.warning("问财 OpenAPI 不可用，无法获取涨停股票")
            return stocks
        
        try:
            result = self.query(f"今日涨停股", perpage=max_stocks)
            
            if isinstance(result, dict):
                captcha_url = result.get('data', {}).get('captcha_url')
                if captcha_url:
                    logger.warning("问财 API 返回验证码要求，数据获取失败")
                    return []
            
            datas = self._parse_answer(result)
            
            for item in datas:
                code = item.get('股票代码', item.get('code', ''))
                name = item.get('股票简称', item.get('名称', ''))
                price = item.get('最新价', item.get('收盘价', 0))
                change_pct = item.get('最新涨跌幅', item.get('涨跌幅', item.get('涨幅', 0)))
                
                reason = item.get('涨停原因类别', item.get('涨停原因', item.get('涨停理由', '')))
                if not reason:
                    for key in item:
                        if '涨停原因' in key or '涨停理由' in key:
                            reason = item[key]
                            break
                
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
        """获取问财人气排名"""
        logger.info(f"获取问财人气排名TOP{top}")
        
        ranks = []
        
        if not self._openapi.is_available():
            logger.warning("问财 OpenAPI 不可用，无法获取人气排名")
            return ranks
        
        try:
            result = self.query(f"人气排名前{top}", perpage=top)
            
            if isinstance(result, dict):
                captcha_url = result.get('data', {}).get('captcha_url')
                if captcha_url:
                    logger.warning("问财 API 返回验证码要求，人气排名获取失败")
                    return []
            
            datas = self._parse_answer(result)
            
            for i, item in enumerate(datas[:top]):
                code = item.get('股票代码', item.get('code', ''))
                name = item.get('股票简称', item.get('name', ''))
                if code and name:
                    code_str = str(code)
                    if '.' in code_str:
                        code_str = code_str.split('.')[0]
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
    
    def is_available(self) -> bool:
        """检查问财服务是否可用"""
        return self._openapi.is_available()
