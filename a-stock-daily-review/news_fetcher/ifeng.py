"""凤凰网热榜采集器"""
import requests
import re
import json
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class IfengCollector(BaseNewsCollector):
    """凤凰网热榜"""

    @property
    def id(self):
        return "ifeng"

    @property
    def name(self):
        return "凤凰网"

    def collect(self) -> List[NewsItem]:
        url = "https://www.ifeng.com/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            return self._parse(resp.text)
        except Exception as e:
            from logger import logger
            logger.warning(f"凤凰网采集失败: {e}")
            return []

    def _parse(self, html: str) -> List[NewsItem]:
        items = []
        
        pattern = r'var\s+allData\s*=\s*(\{[\s\S]*?\});'
        match = re.search(pattern, html)
        if not match:
            return items
        
        try:
            data = json.loads(match.group(1))
        except:
            return items
        
        for news in data.get("hotNews1", [])[:20]:
            title = news.get("title", "")
            if not title:
                continue
            items.append(NewsItem(
                id=news.get("url", title),
                title=title,
                url=news.get("url", ""),
                pub_date=datetime.now(),
                source=self.name,
                extra=news.get("newsTime", ""),
            ))
        
        return items
