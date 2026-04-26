"""36氪快讯采集器"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class Kr36Collector(BaseNewsCollector):
    """36氪快讯"""

    @property
    def id(self):
        return "36kr"

    @property
    def name(self):
        return "36氪快讯"

    def collect(self) -> List[NewsItem]:
        url = "https://www.36kr.com/newsflashes"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            return self._parse(resp.text)
        except Exception as e:
            from logger import logger
            logger.warning(f"36氪采集失败: {e}")
            return []

    def _parse(self, html: str) -> List[NewsItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        
        for div in soup.select(".newsflash-item")[:20]:
            link = div.select_one("a.item-title")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title:
                continue
            
            items.append(NewsItem(
                id=href,
                title=title,
                url=href if href.startswith("http") else f"https://www.36kr.com{href}",
                pub_date=datetime.now(),
                source=self.name,
            ))
        
        return items
