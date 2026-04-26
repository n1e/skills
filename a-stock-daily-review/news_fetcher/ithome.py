"""IT之家热榜采集器"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from .base import BaseNewsCollector
from models.news import NewsItem


class ITHomeCollector(BaseNewsCollector):
    """IT之家热榜采集器"""

    @property
    def id(self):
        return "ithome"

    @property
    def name(self):
        return "IT之家"

    def collect(self) -> List[NewsItem]:
        url = "https://www.ithome.com/list/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            return self._parse(resp.text)
        except Exception as e:
            from logger import logger
            logger.warning(f"IT之家采集失败: {e}")
            return []

    def _parse(self, html: str) -> List[NewsItem]:
        soup = BeautifulSoup(html, "lxml")
        items = []
        ad_keywords = ["神券", "优惠", "补贴", "京东"]
        
        for li in soup.select("#list > div.fl > ul > li"):
            link = li.select_one("a.t")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href:
                continue
            if any(kw in title for kw in ad_keywords):
                continue
            if "lapin" in href:
                continue
            
            items.append(NewsItem(
                id=href,
                title=title,
                url=href if href.startswith("http") else f"https://www.ithome.com{href}",
                pub_date=datetime.now(),
                source=self.name,
            ))
        return items
