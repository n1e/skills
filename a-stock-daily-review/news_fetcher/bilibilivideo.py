"""B站热门视频采集器"""
import requests
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class BilibiliVideoCollector(BaseNewsCollector):
    """B站热门视频"""

    @property
    def id(self):
        return "bilibili_video"

    @property
    def name(self):
        return "哔哩哔哩热门视频"

    def collect(self) -> List[NewsItem]:
        url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"B站视频采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for item in data.get("data", {}).get("list", [])[:20]:
            title = item.get("title", "")
            if not title:
                continue
            view = item.get("view", "")
            items.append(NewsItem(
                id=str(item.get("aid", title)),
                title=title,
                url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                pub_date=datetime.now(),
                source=self.name,
                extra=f"{view}播放",
            ))
        return items
