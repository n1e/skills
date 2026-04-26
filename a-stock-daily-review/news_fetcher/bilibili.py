"""哔哩哔哩热搜采集器"""
import requests
from urllib.parse import quote
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class BilibiliCollector(BaseNewsCollector):
    """哔哩哔哩热搜采集器"""

    @property
    def id(self):
        return "bilibili"

    @property
    def name(self):
        return "哔哩哔哩"

    def collect(self) -> List[NewsItem]:
        url = "https://s.search.bilibili.com/main/hotword?limit=30"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"B站采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for item in data.get("list", []):
            keyword = item.get("keyword", "")
            show_name = item.get("show_name", "") or keyword
            if not show_name:
                continue

            items.append(NewsItem(
                id=keyword,
                title=show_name,
                url=f"https://search.bilibili.com/all?keyword={quote(keyword)}",
                pub_date=datetime.now(),
                source=self.name,
                icon=item.get("icon", ""),
            ))
        return items
