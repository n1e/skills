#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置器
提供彩色日志输出和可配置的日志级别
"""

import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        levelname = record.levelname
        message = record.getMessage()
        
        if self.use_colors and levelname in self.COLORS:
            color = self.COLORS[levelname]
            reset = self.COLORS['RESET']
            formatted = f"{color}{levelname:8s}{reset} {message}"
        else:
            formatted = f"{levelname:8s} {message}"
        
        # 添加时间戳（仅ERROR及以上级别）
        if record.levelno >= logging.ERROR:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted = f"[{timestamp}] {formatted}"
        
        return formatted


def setup_logger(
    name: str = 'a-stock-review',
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    配置并返回日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        use_colors: 是否使用彩色输出
    
    Returns:
        配置好的日志器实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter(use_colors))
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# 默认日志器实例
logger = setup_logger()