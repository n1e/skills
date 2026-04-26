"""牛客网热榜采集器"""
import requests
import time
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class NowcoderCollector(BaseNewsCollector):
    """牛客网热榜"""

    @property
    def id(self):
        return "nowcoder"

    @property
    def name(self):
        return "牛客网"

    def collect(self) -> List[NewsItem]:
        timestamp = int(time.time() * 1000)
        url = f"https://gw-c.nowcoder.com/api/sparta/hot-search/top-hot-pc?size=20&_={timestamp}&t="
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            from logger import logger
            logger.warning(f"牛客网采集失败: {e}")
            return []

    def _parse(self, data: dict) -> List[NewsItem]:
        items = []
        for k in data.get("data", {}).get("result", []):
            item_type = k.get("type", -1)
            if item_type == 74:
                item_url = f"https://www.nowcoder.com/feed/main/detail/{k.get('uuid', '')}"
                item_id = k.get("uuid", "")
            elif item_type == 0:
                item_url = f"https://www.nowcoder.com/discuss/{k.get('id', '')}"
                item_id = k.get("id", "")
            else:
                continue
            
            items.append(NewsItem(
                id=item_id,
                title=k.get("title", ""),
                url=item_url,
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
