"""Solidot采集器"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class SolidotCollector(BaseNewsCollector):
    """Solidot"""

    @property
    def id(self):
        return "solidot"

    @property
    def name(self):
        return "Solidot"

    def collect(self) -> List[NewsItem]:
        items = []
        try:
            url = "https://www.solidot.org/index.rss"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.select("item"):
                title = item.title.text if item.title else ""
                link = item.link.text if item.link else ""
                if title and link:
                    items.append(NewsItem(
                        id=link,
                        title=title,
                        url=link,
                        pub_date=datetime.now(),
                        source=self.name
                    ))
        except Exception as e:
            from logger import logger
            logger.warning(f"Solidot采集失败: {e}")
        return items
