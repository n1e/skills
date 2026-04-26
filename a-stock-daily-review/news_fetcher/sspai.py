"""少数派热榜采集器"""
import requests
import time
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class SspaiCollector(BaseNewsCollector):
    """少数派热榜"""

    @property
    def id(self):
        return "sspai"

    @property
    def name(self):
        return "少数派"

    def collect(self) -> List[NewsItem]:
        timestamp = int(time.time() * 1000)
        url = f"https://sspai.com/api/v1/article/tag/page/get?limit=30&offset=0&created_at={timestamp}&tag=%E7%83%AD%E9%97%A8%E6%96%87%E7%AB%A0&released=false"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"少数派采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for item in data.get("data", [])[:30]:
            title = item.get("title", "")
            if not title:
                continue
            items.append(NewsItem(
                id=str(item.get("id", title)),
                title=title,
                url=f"https://sspai.com/post/{item.get('id', '')}",
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
