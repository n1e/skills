"""澎湃新闻热榜采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class ThepaperCollector(BaseNewsCollector):
    """澎湃新闻热榜"""

    @property
    def id(self):
        return "thepaper"

    @property
    def name(self):
        return "澎湃新闻"

    def collect(self) -> List[NewsItem]:
        url = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"澎湃采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        hot_news = data.get("data", {}).get("hotNews", [])
        for item in hot_news[:20]:
            cont_id = item.get("contId", "")
            items.append(NewsItem(
                id=cont_id,
                title=item.get("name", ""),
                url=f"https://www.thepaper.cn/newsDetail_forward_{cont_id}",
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
