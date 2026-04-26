"""新闻采集器模块 - 从多个站点采集新闻热榜"""
from .base import BaseNewsCollector
from .weibo import WeiboCollector
from .zhihu import ZhihuCollector
from .bilibili import BilibiliCollector
from .baidu import BaiduCollector
from .wallstreetcn import WallstreetcnCollector


COLLECTORS = {
    "weibo": WeiboCollector,
    "zhihu": ZhihuCollector,
    "bilibili": BilibiliCollector,
    "baidu": BaiduCollector,
    "wallstreetcn": WallstreetcnCollector,
}


def get_all_collectors():
    """获取所有可用的采集器"""
    return {k: v for k, v in COLLECTORS.items() if v is not None}


def get_collector_names():
    """获取采集器名称列表"""
    return list(get_all_collectors().keys())
