"""百度热搜采集器"""
import requests
import re
import json
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class BaiduCollector(BaseNewsCollector):
    """百度热搜采集器"""

    @property
    def id(self):
        return "baidu"

    @property
    def name(self):
        return "百度热搜"

    def collect(self) -> List[NewsItem]:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            return self._parse(resp.text)
        except Exception as e:
            from logger import logger
            logger.warning(f"百度采集失败: {e}")
            return []

    def _parse(self, html: str) -> List[NewsItem]:
        items = []
        
        match = re.search(r'<!--s-data:([\s\S]*?)-->', html)
        if not match:
            return items
        
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return items
        
        cards = data.get("data", {}).get("cards", [])
        for card in cards:
            for content in card.get("content", []):
                if content.get("isTop"):
                    continue
                word = content.get("word", "")
                if not word:
                    continue
                raw_url = content.get("rawUrl", "")
                items.append(NewsItem(
                    id=raw_url if raw_url else word,
                    title=word,
                    url=raw_url if raw_url.startswith("http") else f"https://top.baidu.com{raw_url}",
                    pub_date=datetime.now(),
                    source=self.name,
                    hover=content.get("desc", ""),
                ))
        
        return items
