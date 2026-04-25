#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问财数据采集器

优先级：
1. 官方 OpenAPI (https://openapi.iwencai.com/v1/query2data) - 优先
2. CLI 方式 (iwencai-skillhub-cli) - 备选
3. 旧 URL 访问方式 - 备选（仅当其他方式都不可用时）

需要配置 IWENCAI_API_KEY 环境变量或在 config.json 中配置
"""

import json
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

try:
    from config import config as global_config
except ImportError:
    global_config = None


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
    """查找hexin_v.js路径（旧 URL 方式使用）"""
    root = _find_project_root()
    js_path = os.path.join(root, 'lib', 'hexin_v.js')
    if os.path.exists(js_path):
        return js_path
    return 'lib/hexin_v.js'


def get_wencai_config() -> Dict[str, Any]:
    """获取问财配置
    
    优先从环境变量读取，然后从 config.json 读取
    """
    config_dict = {
        'api_key': '',
        'skill_name': '财务数据查询',
        'prefer_openapi': True,
        'prefer_cli': True,
    }
    
    # 从环境变量读取
    env_api_key = os.environ.get('IWENCAI_API_KEY', '')
    if env_api_key:
        config_dict['api_key'] = env_api_key
    
    # 从 config.json 读取
    if global_config:
        json_api_key = global_config.get('wencai.api_key', '')
        if json_api_key and not config_dict['api_key']:
            config_dict['api_key'] = json_api_key
        
        skill_name = global_config.get('wencai.skill_name', '')
        if skill_name:
            config_dict['skill_name'] = skill_name
        
        prefer_openapi = global_config.get('wencai.prefer_openapi', True)
        config_dict['prefer_openapi'] = prefer_openapi
        
        prefer_cli = global_config.get('wencai.prefer_cli', True)
        config_dict['prefer_cli'] = prefer_cli
    
    return config_dict


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
    这是当前优先使用的方式
    
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
            
            # 检查响应
            if isinstance(result, dict):
                status_code = result.get("status_code", 0)
                if status_code != 0:
                    status_msg = result.get("status_msg", "未知错误")
                    logger.warning(f"OpenAPI 返回错误: status_code={status_code}, msg={status_msg}")
                    return None
                
                # 返回完整结果
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


class WencaiCLI:
    """
    问财官方 CLI 客户端（备选）
    
    使用 iwencai-skillhub-cli 进行数据查询
    """
    
    def __init__(self):
        self._config = get_wencai_config()
        self._api_key = self._config.get('api_key', '')
        self._cli_available = None
        self._installed_skills = set()
    
    def _check_cli_available(self) -> bool:
        """检查 CLI 是否可用"""
        if self._cli_available is not None:
            return self._cli_available
        
        try:
            result = subprocess.run(
                ['iwencai-skillhub-cli', '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            self._cli_available = result.returncode == 0
            if self._cli_available:
                logger.info("问财 CLI 可用")
            else:
                logger.warning("问财 CLI 不可用")
        except FileNotFoundError:
            self._cli_available = False
            logger.warning("问财 CLI 未安装")
        except Exception as e:
            self._cli_available = False
            logger.warning(f"检查问财 CLI 失败: {e}")
        
        return self._cli_available
    
    def _check_api_key(self) -> bool:
        """检查 API Key 是否配置"""
        if not self._api_key:
            logger.warning("IWENCAI_API_KEY 未配置（请设置环境变量或在 config.json 中配置）")
            return False
        return True
    
    def _install_skill(self, skill_name: str) -> bool:
        """安装技能"""
        if skill_name in self._installed_skills:
            return True
        
        if not self._check_cli_available():
            return False
        
        try:
            logger.info(f"安装问财技能: {skill_name}")
            result = subprocess.run(
                ['iwencai-skillhub-cli', 'install', skill_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                self._installed_skills.add(skill_name)
                logger.info(f"技能 {skill_name} 安装成功")
                return True
            else:
                logger.warning(f"技能 {skill_name} 安装失败: {result.stderr}")
                return False
        except Exception as e:
            logger.warning(f"安装技能失败: {e}")
            return False
    
    def query(self, question: str, skill_name: str = "财务数据查询") -> Optional[Dict]:
        """
        使用 CLI 执行查询
        
        Args:
            question: 查询问题
            skill_name: 技能名称
            
        Returns:
            查询结果字典，失败返回 None
        """
        if not self._check_cli_available():
            return None
        
        if not self._check_api_key():
            return None
        
        self._install_skill(skill_name)
        
        try:
            logger.info(f"使用问财 CLI 查询: {question}")
            
            cmd = [
                'iwencai-skillhub-cli',
                'run',
                skill_name,
                '--question',
                question
            ]
            
            env = os.environ.copy()
            env['IWENCAI_API_KEY'] = self._api_key
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            if result.returncode != 0:
                logger.warning(f"CLI 查询失败: {result.stderr}")
                return None
            
            output = result.stdout.strip()
            try:
                data = json.loads(output)
                logger.info("CLI 查询成功")
                return data
            except json.JSONDecodeError:
                logger.warning(f"CLI 输出不是 JSON: {output[:200]}")
                return {'raw_output': output}
                
        except Exception as e:
            logger.warning(f"CLI 查询异常: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查 CLI 是否完全可用"""
        return self._check_cli_available() and self._check_api_key()


class WencaiOldURL:
    """
    旧 URL 访问方式（备选）
    
    仅当 OpenAPI 和 CLI 都不可用时使用
    """
    
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
        """初始化问财会话"""
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
        """使用旧 URL 方式执行查询"""
        self._init_session()
        
        hexin_v = self._generate_hexin_v()
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
        
        try:
            resp = self.session.post(
                'https://www.iwencai.com/customized/chart/get-robot-data',
                headers=headers,
                json=payload,
                cookies=self.cookies,
                timeout=30
            )
            return resp.json()
        except Exception as e:
            logger.error(f"旧 URL 查询失败: {e}")
            return {}


class WencaiFetcher:
    """
    问财数据采集器
    
    优先级：
    1. 官方 OpenAPI (https://openapi.iwencai.com/v1/query2data) - 优先
    2. CLI 方式 (iwencai-skillhub-cli) - 备选
    3. 旧 URL 访问方式 - 备选
    """
    
    def __init__(self):
        self._config = get_wencai_config()
        self._prefer_openapi = self._config.get('prefer_openapi', True)
        self._prefer_cli = self._config.get('prefer_cli', True)
        self._skill_name = self._config.get('skill_name', '财务数据查询')
        
        # OpenAPI 客户端（优先）
        self._openapi = WencaiOpenAPI()
        
        # CLI 客户端（备选）
        self._cli = WencaiCLI()
        
        # 旧 URL 客户端（备选）
        self._old_url = WencaiOldURL()
    
    def query(self, question: str, perpage: int = 100) -> dict:
        """
        执行问财查询
        
        优先级：
        1. OpenAPI（如果配置了 API_KEY）
        2. CLI
        3. 旧 URL
        
        Args:
            question: 查询问题
            perpage: 每页条数（用于 OpenAPI 和旧 URL）
            
        Returns:
            查询结果字典
        """
        # 1. 优先使用 OpenAPI
        if self._prefer_openapi and self._openapi.is_available():
            result = self._openapi.query(question, limit=str(perpage))
            if result:
                # 转换为标准格式
                return self._convert_openapi_result(result)
        
        # 2. 使用 CLI
        if self._prefer_cli and self._cli.is_available():
            result = self._cli.query(question, skill_name=self._skill_name)
            if result and 'raw_output' not in result:
                return result
        
        # 3. 使用旧 URL
        logger.info("使用旧 URL 访问方式查询...")
        return self._old_url.query(question, perpage)
    
    def _convert_openapi_result(self, openapi_result: Dict) -> Dict:
        """
        将 OpenAPI 返回结果转换为旧 URL 方式的格式
        
        OpenAPI 返回格式：
        {
            "datas": [...],
            "code_count": N,
            "chunks_info": {},
            "status_code": 0
        }
        
        旧 URL 返回格式：
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
        
        if 'raw_output' in data:
            logger.warning("CLI 返回原始输出，无法解析")
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
        """获取指定天数的成交额历史（使用A股总成交金额，单位：元）"""
        logger.info(f"获取最近{days}日成交额历史")
        volumes = []
        
        try:
            result = self.query(f"同花顺全A成交金额 最近{days}个交易日", perpage=days)
            
            if isinstance(result, dict):
                captcha_url = result.get('data', {}).get('captcha_url')
                if captcha_url:
                    logger.warning("问财 API 返回验证码要求，数据获取失败")
                    return []
            
            datas = self._parse_answer(result)
            
            for item in datas:
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
