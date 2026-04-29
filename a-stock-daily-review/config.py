#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器
从config.json加载配置，同时支持从环境变量读取敏感配置
环境变量优先级高于配置文件
支持配置热更新和变更回调
"""

import json
import os
import threading
from typing import Dict, Any, List, Callable, Optional

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
        
        self._config_path = config_path
        self._config = self._load_config(config_path)
        self._merge_env_vars()
        self._change_callbacks: Dict[str, List[Callable]] = {}
        self._global_callbacks: List[Callable] = []
        self._lock = threading.Lock()
    
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
    
    def save(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否保存成功
        """
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def on_change(self, key: str = None, callback: Callable = None):
        """
        注册配置变更回调
        
        Args:
            key: 配置键（支持点号分隔的嵌套键），None表示全局回调
            callback: 回调函数，签名为 callback(key, old_value, new_value)
        """
        if callback is None:
            return
        
        with self._lock:
            if key is None:
                if callback not in self._global_callbacks:
                    self._global_callbacks.append(callback)
            else:
                if key not in self._change_callbacks:
                    self._change_callbacks[key] = []
                if callback not in self._change_callbacks[key]:
                    self._change_callbacks[key].append(callback)
    
    def remove_callback(self, key: str = None, callback: Callable = None):
        """
        移除配置变更回调
        
        Args:
            key: 配置键，None表示全局回调
            callback: 回调函数
        """
        with self._lock:
            if key is None:
                if callback in self._global_callbacks:
                    self._global_callbacks.remove(callback)
            else:
                if key in self._change_callbacks and callback in self._change_callbacks[key]:
                    self._change_callbacks[key].remove(callback)
    
    def _notify_callbacks(self, key: str, old_value: Any, new_value: Any):
        """
        通知配置变更回调
        
        Args:
            key: 配置键
            old_value: 旧值
            new_value: 新值
        """
        # 通知全局回调
        for callback in self._global_callbacks:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                logger.error(f"配置变更回调执行失败: {e}")
        
        # 通知特定键的回调
        if key in self._change_callbacks:
            for callback in self._change_callbacks[key]:
                try:
                    callback(key, old_value, new_value)
                except Exception as e:
                    logger.error(f"配置变更回调执行失败: {e}")
        
        # 检查是否需要通知父级键的回调
        keys = key.split('.')
        for i in range(1, len(keys)):
            parent_key = '.'.join(keys[:i])
            if parent_key in self._change_callbacks:
                for callback in self._change_callbacks[parent_key]:
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        logger.error(f"配置变更回调执行失败: {e}")
    
    def set_and_notify(self, key: str, value: Any) -> bool:
        """
        设置配置项并通知回调（支持热生效）
        
        Args:
            key: 配置键
            value: 新值
            
        Returns:
            是否设置成功且值有变化
        """
        with self._lock:
            old_value = self.get(key)
            
            # 检查值是否真的变化了
            if old_value == value:
                logger.debug(f"配置值未变化，跳过: {key}")
                return False
            
            # 设置新值
            self.set(key, value)
            
            # 通知回调
            logger.info(f"配置变更: {key} = {value} (原值: {old_value})")
            self._notify_callbacks(key, old_value, value)
            
            return True
    
    def update_from_dict(self, config_dict: Dict[str, Any], save: bool = True) -> Dict[str, bool]:
        """
        从字典批量更新配置
        
        Args:
            config_dict: 配置字典（支持嵌套结构）
            save: 是否保存到文件
            
        Returns:
            每个配置键的更新结果字典
        """
        def _flatten_dict(d: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
            """将嵌套字典展平为点号分隔的键"""
            result = {}
            for k, v in d.items():
                new_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict) and v:
                    result.update(_flatten_dict(v, new_key))
                else:
                    result[new_key] = v
            return result
        
        # 展平配置字典
        flat_config = _flatten_dict(config_dict)
        
        results = {}
        changed = False
        
        for key, value in flat_config.items():
            was_changed = self.set_and_notify(key, value)
            results[key] = was_changed
            if was_changed:
                changed = True
        
        # 保存到文件
        if save and changed:
            self.save()
        
        return results
    
    def reload(self) -> bool:
        """
        重新从文件加载配置
        
        Returns:
            是否加载成功
        """
        try:
            new_config = self._load_config(self._config_path)
            
            with self._lock:
                old_config = self._config.copy()
                self._config = new_config
                self._merge_env_vars()
                
                # 通知所有变更
                def _compare_and_notify(old: Dict, new: Dict, prefix: str = ''):
                    all_keys = set(list(old.keys()) + list(new.keys()))
                    for key in all_keys:
                        full_key = f"{prefix}.{key}" if prefix else key
                        old_val = old.get(key)
                        new_val = new.get(key)
                        
                        if isinstance(old_val, dict) and isinstance(new_val, dict):
                            _compare_and_notify(old_val, new_val, full_key)
                        elif old_val != new_val:
                            self._notify_callbacks(full_key, old_val, new_val)
                
                _compare_and_notify(old_config, self._config)
            
            logger.info(f"配置已重新加载: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return False
    
    def get_config_path(self) -> str:
        """
        获取配置文件路径
        
        Returns:
            配置文件路径
        """
        return self._config_path


# 全局配置实例
config = Config()