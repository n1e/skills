"""华尔街见闻采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class WallstreetcnCollector(BaseNewsCollector):
    """华尔街见闻"""

    @property
    def id(self):
        return "wallstreetcn"

    @property
    def name(self):
        return "华尔街见闻"

    def collect(self) -> List[NewsItem]:
        url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"华尔街见闻采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for item in data.get("data", {}).get("items", []):
            title = item.get("title", "")
            if title == "":
                title = item.get("content_text", "")
            if not title:
                continue
            items.append(NewsItem(
                id=str(item.get("id", title)),
                title=title,
                url=item.get("uri", ""),
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
