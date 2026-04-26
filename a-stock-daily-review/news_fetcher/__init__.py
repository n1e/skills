"""新闻采集器模块 - 从多个站点采集新闻热榜"""
from .base import BaseNewsCollector
from .weibo import WeiboCollector
from .zhihu import ZhihuCollector
from .bilibili import BilibiliCollector
from .bilibilivideo import BilibiliVideoCollector
from .baidu import BaiduCollector
from .douyin import DouyinCollector
from .ithome import ITHomeCollector
from .juejin import JuejinCollector
from .hupu import HupuCollector
from .tieba import TiebaCollector
from .douban import DoubanCollector
from .sspai import SspaiCollector
from .nowcoder import NowcoderCollector
from .wallstreetcn import WallstreetcnCollector
from .ifeng import IfengCollector
from .thepaper import ThepaperCollector
from .kr36 import Kr36Collector
from .solidot import SolidotCollector


COLLECTORS = {
    "weibo": WeiboCollector,
    "zhihu": ZhihuCollector,
    "bilibili": BilibiliCollector,
    "bilibili_video": BilibiliVideoCollector,
    "baidu": BaiduCollector,
    "douyin": DouyinCollector,
    "ithome": ITHomeCollector,
    "juejin": JuejinCollector,
    "hupu": HupuCollector,
    "tieba": TiebaCollector,
    "douban": DoubanCollector,
    "sspai": SspaiCollector,
    "nowcoder": NowcoderCollector,
    "wallstreetcn": WallstreetcnCollector,
    "ifeng": IfengCollector,
    "thepaper": ThepaperCollector,
    "36kr": Kr36Collector,
    "solidot": SolidotCollector,
}


def get_all_collectors():
    """获取所有可用的采集器"""
    return {k: v for k, v in COLLECTORS.items() if v is not None}


def get_collector_names():
    """获取采集器名称列表"""
    return list(get_all_collectors().keys())
