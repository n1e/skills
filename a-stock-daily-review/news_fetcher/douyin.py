"""抖音热榜采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class DouyinCollector(BaseNewsCollector):
    """抖音热榜采集器"""

    @property
    def id(self):
        return "douyin"

    @property
    def name(self):
        return "抖音"

    def collect(self) -> List[NewsItem]:
        url = "https://aweme.snssdk.com/aweme/v1/hot/search/list/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"抖音采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        word_list = data.get("data", {}).get("word_list", [])
        for item in word_list:
            title = item.get("sentence", "") or item.get("word", "")
            if not title:
                continue
            hot_value = item.get("hot_value", 0)
            items.append(NewsItem(
                id=item.get("word", title),
                title=title,
                url=f"https://www.douyin.com/search/{item.get('word', '')}",
                pub_date=datetime.now(),
                source=self.name,
                extra=str(hot_value) if hot_value else "",
            ))
        return items
