#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证器和标准化器
"""

import re
from typing import Tuple, Optional


def normalize_stock_code(code: str) -> str:
    """
    标准化股票代码
    统一转换为6位数字，移除SH/SZ前缀
    
    Args:
        code: 原始股票代码（如：'SH600519', 'SZ000001', '600519']
    
    Returns:
        标准化后的6位数字代码
    """
    if not code:
        return ""
    
    # 移除所有非数字字符
    code = re.sub(r'[^\d]', '', code)
    
    # 确保是6位数字
    if len(code) == 6 and code.isdigit():
        return code
    
    return ""


def is_valid_stock_code(code: str) -> bool:
    """
    验证股票代码格式是否正确
    
    Args:
        code: 股票代码
    
    Returns:
        是否为有效的A股代码（6位数字）
    """
    normalized = normalize_stock_code(code)
    return len(normalized) == 6 and normalized.isdigit()


def split_market_prefix(code: str) -> Tuple[str, str]:
    """
    分离市场前缀和股票代码
    
    Args:
        code: 带有市场前缀的代码（如'SH600519'）
    
    Returns:
        (market_prefix, normalized_code) 市场前缀和标准化代码的元组
    """
    code = code.strip().upper()
    
    if code.startswith('SH'):
        return ('SH', code[2:])
    elif code.startswith('SZ'):
        return ('SZ', code[2:])
    else:
        return ('', code)


def format_code_with_prefix(code: str, market: str = '') -> str:
    """
    格式化代码为带前缀的格式
    
    Args:
        code: 股票代码
        market: 市场前缀（'SH'或'SZ'）
    
    Returns:
        格式化后的代码（如：'SH600519'）
    """
    normalized = normalize_stock_code(code)
    if not normalized:
        return ""
    
    if market:
        return f"{market.upper()}{normalized}"
    
    # 自动判断市场
    if normalized.startswith('6'):
        return f"SH{normalized}"
    elif normalized.startswith('0') or normalized.startswith('3'):
        return f"SZ{normalized}"
    
    return normalized


def validate_market_data(data: dict) -> bool:
    """
    验证大盘数据字典的完整性
    
    Args:
        data: 大盘数据字典
    
    Returns:
        数据是否有效
    """
    required_fields = ['up_count', 'down_count', 'limit_up_count', 'limit_down_count']
    
    for field in required_fields:
        if field not in data:
            return False
    
    # 确保所有数值都是非负整数
    for field in required_fields:
        try:
            value = int(data[field])
            if value < 0:
                return False
        except (ValueError, TypeError):
            return False
    
    return True