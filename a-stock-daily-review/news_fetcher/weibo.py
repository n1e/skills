"""微博热榜采集器"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from .base import BaseNewsCollector, NewsItem


class WeiboCollector(BaseNewsCollector):
    """微博热榜"""

    @property
    def id(self):
        return "weibo"

    @property
    def name(self):
        return "微博"

    def collect(self) -> List[NewsItem]:
        baseURL = "https://s.weibo.com"
        url = baseURL + "/top/summary?cate=realtimehot"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Cookie": "SUB=_2AkMWIuNSf8NxqwJRmP8dy2rhaoV2ygrEieKgfhKJJRMxHRl-yT9jqk86tRB6PaLNvQZR6zYUcYVT1zSjoSreQHidcUq7",
            "Referer": url,
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            return self._parse(resp.text)
        except Exception as e:
            from logger import logger
            logger.warning(f"微博采集失败: {e}")
            return []

    def _parse(self, html: str) -> List[NewsItem]:
        items = []

        soup = BeautifulSoup(html, "lxml")

        table = soup.select_one("#pl_top_realtimehot table")
        if not table:
            return items

        for tr in table.select("tbody tr"):
            rank_td = tr.select_one("td.td-01")
            if rank_td:
                rank_text = rank_td.get_text(strip=True)
                if not rank_text.isdigit():
                    continue
                if int(rank_text) <= 0:
                    continue

            link = tr.select_one("td.td-02 a")
            if not link:
                continue

            href = link.get("href", "")
            title = link.get_text(strip=True)

            if not title or not href or "javascript" in href:
                continue

            items.append(NewsItem(
                id=title,
                title=title,
                url=f"https://s.weibo.com{href}",
                pub_date=datetime.now(),
                source=self.name,
            ))

        return items
