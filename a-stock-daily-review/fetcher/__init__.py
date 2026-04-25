#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集器包
"""

from .base import Fetcher
from .wencai import WencaiFetcher
from .xueqiu import XueqiuFetcher
from .eastmoney import EastmoneyFetcher
from .legu import LeguFetcher
from .funddb import FunddbFetcher, FearGreedData

__all__ = [
    'Fetcher',
    'WencaiFetcher',
    'XueqiuFetcher',
    'EastmoneyFetcher',
    'LeguFetcher',
    'FunddbFetcher',
    'FearGreedData'
]