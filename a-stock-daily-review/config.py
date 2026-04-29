#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
从config.json加载配置，同时支持从环境变量读取敏感配置
环境变量优先级高于配置文件
"""

import json
import os
from typing import Dict, Any

from logger import setup_logger, logger


class Config:
    """配置管理器"""
    
    # 环境变量映射
    ENV_VAR_MAPPING = {
        # 飞书配置
        'push.feishu.app_id': 'FS_ID',
        'push.feishu.app_secret': 'FS_KEY',
        'push.feishu.chat_id': 'FS_CHAT_ID',
        
        # 邮件配置
        'push.email.smtp_host': 'SMTP_HOST',
        'push.email.smtp_port': 'SMTP_PORT',
        'push.email.smtp_user': 'SMTP_USER',
        'push.email.smtp_password': 'SMTP_PASSWORD',
        'push.email.from_email': 'FROM_EMAIL',
        'push.email.to_emails': 'TO_EMAILS',
    }
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'config.json')
        
        self._config = self._load_config(config_path)
        self._merge_env_vars()
    
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
                },
                "push": {
                    "enabled": False,
                    "feishu": {
                        "enabled": False,
                        "app_id": "",
                        "app_secret": "",
                        "chat_id": ""
                    },
                    "email": {
                        "enabled": False,
                        "smtp_host": "",
                        "smtp_port": 587,
                        "smtp_user": "",
                        "smtp_password": "",
                        "from_email": "",
                        "to_emails": []
                    }
                }
            }
    
    def _merge_env_vars(self):
        """从环境变量读取配置并合并（环境变量优先级高于配置文件）"""
        for config_key, env_var in self.ENV_VAR_MAPPING.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # 特殊处理某些类型
                if config_key == 'push.email.smtp_port':
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        continue  # 保持默认值
                elif config_key == 'push.email.to_emails':
                    # 支持逗号分隔的邮箱列表
                    env_value = [e.strip() for e in env_value.split(',') if e.strip()]
                
                # 设置配置值
                self.set(config_key, env_value)
                logger.info(f"从环境变量加载配置: {config_key}")
    
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