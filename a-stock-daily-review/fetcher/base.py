#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集器基类
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger('a-stock-review')


class Fetcher(ABC):
    """数据采集器抽象基类"""
    
    def __init__(self):
        self.session = None
    
    @abstractmethod
    def fetch(self, *args, **kwargs) -> Any:
        """执行数据采集"""
        pass
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Any:
        """发起HTTP请求（带重试机制）"""
        import requests
        from utils.retry import retry_with_backoff
        
        @retry_with_backoff(initial_delay=1.0, max_delay=10.0, max_attempts=3)
        def _request():
            if method.upper() == 'GET':
                resp = self.session.get(url, **kwargs)
            else:
                resp = self.session.post(url, **kwargs)
            resp.raise_for_status()
            return resp
        
        try:
            return _request()
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            raise