#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书推送器
实现飞书消息推送功能
"""

import os
import json
import requests
from typing import Optional, Dict, Any

from logger import logger
from pusher.base import BasePusher


class FeishuPusher(BasePusher):
    """飞书推送器"""
    
    # API 端点
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/files"
    SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化飞书推送器
        
        Args:
            config: 飞书配置，包含 app_id, app_secret, chat_id
        """
        super().__init__(config)
        self.app_id = config.get('app_id', '')
        self.app_secret = config.get('app_secret', '')
        self.chat_id = config.get('chat_id', '')
        
        # 从环境变量获取配置（如果配置文件中没有）
        if not self.app_id:
            self.app_id = os.environ.get('FS_ID', '')
        if not self.app_secret:
            self.app_secret = os.environ.get('FS_KEY', '')
        if not self.chat_id:
            self.chat_id = os.environ.get('FS_CHAT_ID', '')
        
        self._access_token = None
        self._token_expire_time = 0
    
    def _get_access_token(self) -> Optional[str]:
        """
        获取飞书访问令牌
        
        Returns:
            访问令牌，失败返回 None
        """
        import time
        
        # 检查令牌是否有效
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token
        
        try:
            logger.info("获取飞书访问令牌...")
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = requests.post(self.TOKEN_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                self._access_token = result.get('tenant_access_token')
                expire = result.get('expire', 7200)
                self._token_expire_time = time.time() + expire - 300  # 提前5分钟过期
                logger.info("飞书访问令牌获取成功")
                return self._access_token
            else:
                logger.error(f"获取飞书访问令牌失败: {result.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            logger.error(f"获取飞书访问令牌异常: {e}")
            return None
    
    def _upload_file(self, file_path: str) -> Optional[str]:
        """
        上传文件到飞书
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件 key，失败返回 None
        """
        token = self._get_access_token()
        if not token:
            return None
        
        try:
            import os
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.info(f"上传文件到飞书: {file_name} ({file_size} 字节)")
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            # 准备表单数据
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f, 'text/html' if file_name.endswith('.html') else 'application/octet-stream')
                }
                
                data = {
                    'file_type': 'stream',
                    'file_name': file_name
                }
                
                response = requests.post(
                    self.UPLOAD_URL,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get('code') == 0:
                    file_key = result.get('data', {}).get('file_key')
                    logger.info(f"文件上传成功，file_key: {file_key}")
                    return file_key
                else:
                    logger.error(f"文件上传失败: {result.get('msg', '未知错误')}")
                    return None
                    
        except Exception as e:
            logger.error(f"上传文件到飞书异常: {e}")
            return None
    
    def _send_file_message(self, file_key: str, title: Optional[str] = None) -> bool:
        """
        发送文件消息到飞书群
        
        Args:
            file_key: 文件 key
            title: 消息标题（可选）
            
        Returns:
            是否发送成功
        """
        token = self._get_access_token()
        if not token:
            return False
        
        try:
            logger.info(f"发送文件消息到飞书群: {self.chat_id}")
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # 构建消息内容
            content = json.dumps({
                'file_key': file_key
            })
            
            payload = {
                'receive_id': self.chat_id,
                'msg_type': 'file',
                'content': content
            }
            
            # 添加查询参数
            params = {
                'receive_id_type': 'chat_id'
            }
            
            response = requests.post(
                self.SEND_URL,
                headers=headers,
                params=params,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                message_id = result.get('data', {}).get('message_id')
                logger.info(f"消息发送成功，message_id: {message_id}")
                return True
            else:
                logger.error(f"消息发送失败: {result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"发送飞书消息异常: {e}")
            return False
    
    def push(self, title: str, content: str, file_path: Optional[str] = None) -> bool:
        """
        推送消息
        
        Args:
            title: 消息标题
            content: 消息内容
            file_path: 附件文件路径（可选）
            
        Returns:
            是否推送成功
        """
        if not self.enabled:
            logger.info("飞书推送已禁用，跳过")
            return False
        
        if not self.app_id or not self.app_secret or not self.chat_id:
            logger.warning("飞书配置不完整，无法推送")
            return False
        
        # 如果有文件路径，优先推送文件
        if file_path:
            return self.push_file(file_path, title)
        
        # 否则推送文本消息（暂不实现，因为主要需求是推送文件）
        logger.warning("飞书文本消息推送暂未实现")
        return False
    
    def push_file(self, file_path: str, title: Optional[str] = None) -> bool:
        """
        推送文件
        
        Args:
            file_path: 文件路径
            title: 文件标题（可选）
            
        Returns:
            是否推送成功
        """
        if not self.enabled:
            logger.info("飞书推送已禁用，跳过")
            return False
        
        if not self.app_id or not self.app_secret or not self.chat_id:
            logger.warning("飞书配置不完整，无法推送")
            return False
        
        import os
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        
        # 上传文件
        file_key = self._upload_file(file_path)
        if not file_key:
            return False
        
        # 发送文件消息
        return self._send_file_message(file_key, title)
