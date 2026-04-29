"""新闻采集器模块 - 从多个站点采集新闻热榜"""
from typing import Dict, List, Optional, Any

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


def get_collectors_by_names(names: List[str]) -> Dict[str, Any]:
    """
    根据名称列表获取采集器（用于配置过滤）
    
    Args:
        names: 采集器名称列表
        
    Returns:
        过滤后的采集器字典
    """
    all_collectors = get_all_collectors()
    result = {}
    
    for name in names:
        name = name.strip()
        if name in all_collectors:
            result[name] = all_collectors[name]
        elif name == "36kr":
            # 兼容36kr的别名
            if "36kr" in all_collectors:
                result[name] = all_collectors["36kr"]
    
    return result


def get_collector_names():
    """获取采集器名称列表"""
    return list(get_all_collectors().keys())
