"""百度贴吧热榜采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class TiebaCollector(BaseNewsCollector):
    """百度贴吧热榜"""

    @property
    def id(self):
        return "tieba"

    @property
    def name(self):
        return "百度贴吧"

    def collect(self) -> List[NewsItem]:
        url = "https://tieba.baidu.com/hottopic/browse/topicList"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"贴吧采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        topic_list = data.get("data", {}).get("bang_topic", {}).get("topic_list", [])
        for item in topic_list[:30]:
            items.append(NewsItem(
                id=str(item.get("topic_id", "")),
                title=item.get("topic_name", ""),
                url=item.get("topic_url", ""),
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
