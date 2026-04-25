#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
从config.json加载配置，提供全局配置访问
"""

import json
import os
from typing import Dict, Any


class Config:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'config.json')
        
        self._config = self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            # 返回默认配置
            return {
                "run_time": "16:00",
                "output_dir": "output",
                "market": {
                    "min_change_pct": 9.5
                },
                "heat_rank": {
                    "top": 50
                },
                "surge": {
                    "min_change_pct": 9.5,
                    "max_stocks": 200
                }
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号分隔的嵌套键）"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """返回完整配置字典"""
        return self._config.copy()


# 全局配置实例
config = Config()