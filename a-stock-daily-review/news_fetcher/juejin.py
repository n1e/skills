"""掘金热榜采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class JuejinCollector(BaseNewsCollector):
    """掘金热榜采集器"""

    @property
    def id(self):
        return "juejin"

    @property
    def name(self):
        return "掘金"

    def collect(self) -> List[NewsItem]:
        url = "https://api.juejin.cn/content_api/v1/content/article_rank?category_id=1&type=hot&spider=0"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"掘金采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for item in data.get("data", [])[:50]:
            content = item.get("content", {})
            title = content.get("title", "")
            if not title:
                continue
            items.append(NewsItem(
                id=content.get("content_id", title),
                title=title,
                url=f"https://juejin.cn/post/{content.get('content_id', '')}",
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
