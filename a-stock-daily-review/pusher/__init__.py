#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送模块
支持飞书和邮件推送
"""

from pusher.base import BasePusher
from pusher.feishu import FeishuPusher
from pusher.email import EmailPusher
from pusher.manager import PushManager

__all__ = ['BasePusher', 'FeishuPusher', 'EmailPusher', 'PushManager']
