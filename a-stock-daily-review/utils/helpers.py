#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用辅助函数
"""

import random
import string
from datetime import datetime


def rand_string(n: int) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def format_number(num: float, unit: str = '', precision: int = 0) -> str:
    """
    格式化数字显示
    
    Args:
        num: 数字
        unit: 单位（如'万'、'亿'）
        precision: 小数位数
    
    Returns:
        格式化后的字符串
    """
    if precision > 0:
        formatted = f"{num:,.{precision}f}"
    else:
        formatted = f"{int(num):,}"
    
    return formatted + unit


def get_trading_date(date: str = None) -> str:
    """
    获取交易日期（如果当天不是交易日，返回最近交易日）
    这里简单返回当前日期或指定日期，实际可以接入交易日历
    
    Args:
        date: 日期字符串（YYYY-MM-DD），默认今天
    
    Returns:
        交易日期字符串
    """
    if date is None:
        return datetime.now().strftime('%Y-%m-%d')
    return date


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法，处理除零错误
    
    Args:
        numerator: 分子
        denominator: 分母
        default: 默认值（除零时返回）
    
    Returns:
        计算结果
    """
    if denominator == 0:
        return default
    return numerator / denominator


def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    截断字符串并添加后缀
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 后缀
    
    Returns:
        截断后的字符串
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix