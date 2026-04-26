"""知乎热榜采集器"""
import requests
import re
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class ZhihuCollector(BaseNewsCollector):
    """知乎热榜采集器"""

    @property
    def id(self):
        return "zhihu"

    @property
    def name(self):
        return "知乎"

    def collect(self) -> List[NewsItem]:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-list-web?limit=20&desktop=true"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.zhihu.com/",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"知乎采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        re_id = re.compile(r"(\d+)$")
        for item in data.get("data", []):
            target = item.get("target", {})
            link = target.get("link", {})
            url = link.get("url", "")
            match = re_id.search(url)
            news_id = match.group(1) if match else url

            title = target.get("title_area", {}).get("text", "")
            excerpt = target.get("excerpt_area", {}).get("text", "")
            metrics = target.get("metrics_area", {}).get("text", "")

            if not title:
                continue

            items.append(NewsItem(
                id=news_id,
                title=title,
                url=url,
                pub_date=datetime.now(),
                source=self.name,
                extra=metrics,
                hover=excerpt,
            ))
        return items
