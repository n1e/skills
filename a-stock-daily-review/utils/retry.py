#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试装饰器
为网络请求添加指数退避重试机制
"""

import time
import functools
import logging
from typing import Callable, TypeVar, Any

logger = logging.getLogger('a-stock-review')


def simple_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    简单的重试装饰器（不使用外部库）
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避乘数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"第{attempt + 1}次重试 {func.__name__}: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"重试失败（{max_attempts}次）{func.__name__}: {e}")
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exponential: bool = True
):
    """
    通用重试装饰器
    
    Args:
        max_attempts: 最大尝试次数（默认3次）
        delay: 初始延迟时间（秒）
        backoff: 退避乘数
        exponential: 是否使用指数退避（True）或固定延迟（False）
    
    Example:
        @retry(max_attempts=3, delay=1.0)
        def fetch_data():
            # 网络请求
            pass
    """
    def decorator(func: Callable) -> Callable:
        return simple_retry(max_attempts, delay, backoff)(func)
    
    return decorator


def retry_with_backoff(
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    max_attempts: int = 5
):
    """
    带最大延迟限制的指数退避重试
    
    Args:
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        multiplier: 乘数
        max_attempts: 最大尝试次数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"第{attempt + 1}次重试 {func.__name__} (delay={delay}s): {e}")
                        time.sleep(min(delay, max_delay))
                        delay *= multiplier
                    else:
                        logger.error(f"重试失败（{max_attempts}次）{func.__name__}: {e}")
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# 尝试使用tenacity（如果已安装）
try:
    import requests
    from tenacity import retry as tenacity_retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    
    def retry_tenacity(
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 10.0
    ):
        """
        使用tenacity库的增强重试（如果可用）
        支持更复杂的重试策略
        """
        def decorator(func: Callable) -> Callable:
            return tenacity_retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
                retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
                reraise=True
            )(func)
        return decorator
    
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False
    logger.debug("tenacity未安装，使用内置重试机制")