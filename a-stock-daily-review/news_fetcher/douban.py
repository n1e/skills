"""豆瓣电影热榜采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class DoubanCollector(BaseNewsCollector):
    """豆瓣电影热榜"""

    @property
    def id(self):
        return "douban"

    @property
    def name(self):
        return "豆瓣电影"

    def collect(self) -> List[NewsItem]:
        url = "https://movie.douban.com/j/search_subjects?type=movie&tag=%E7%83%AD%E9%97%A8&sort=rank&page_limit=20"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://movie.douban.com/"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"豆瓣采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for item in data.get("subjects", [])[:20]:
            title = item.get("title", "")
            if not title:
                continue
            rate = item.get("rate", "")
            items.append(NewsItem(
                id=str(item.get("id", title)),
                title=title,
                url=item.get("url", ""),
                pub_date=datetime.now(),
                source=self.name,
                extra=rate,
            ))
        return items
