#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻资讯相关数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class NewsItem:
    """新闻条目"""
    id: str = ""
    title: str = ""
    url: str = ""
    pub_date: datetime = field(default_factory=datetime.now)
    source: str = ""
    extra: Optional[str] = None
    hover: Optional[str] = None
    icon: Optional[str] = None


@dataclass
class CompositeNewsRank:
    """复合资讯热度排名"""
    title: str = ""
    representative_url: str = ""
    composite_score: float = 0.0
    source_count: int = 0
    sources: List[str] = field(default_factory=list)
    related_news: List[NewsItem] = field(default_factory=list)
    avg_hot_score: float = 0.0
    rank: int = 0
