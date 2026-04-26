"""基础采集器类定义"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from models.news import NewsItem


class BaseNewsCollector(ABC):
    """新闻采集器基类"""

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def collect(self) -> List[NewsItem]:
        pass
