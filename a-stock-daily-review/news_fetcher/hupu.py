"""虎扑步行街采集器"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class HupuCollector(BaseNewsCollector):
    """虎扑步行街热榜"""

    @property
    def id(self):
        return "hupu"

    @property
    def name(self):
        return "虎扑步行街"

    def collect(self) -> List[NewsItem]:
        url = "https://bbs.hupu.com/topic-daily-hot"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            return self._parse(resp.text)
        except Exception as e:
            from logger import logger
            logger.warning(f"虎扑采集失败: {e}")
            return []

    def _parse(self, html: str) -> List[NewsItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        
        for li in soup.select("li.bbs-sl-web-post-body")[:50]:
            link = li.select_one("a.p-title")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title:
                continue
            
            items.append(NewsItem(
                id=href,
                title=title,
                url=href if href.startswith("http") else f"https://bbs.hupu.com{href}",
                pub_date=datetime.now(),
                source=self.name,
            ))
        
        return items
